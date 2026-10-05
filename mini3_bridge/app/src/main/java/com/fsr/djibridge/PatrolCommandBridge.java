package com.fsr.djibridge;

import android.os.SystemClock;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import dji.sdk.keyvalue.value.flightcontroller.*;
import dji.v5.common.callback.CommonCallbacks;
import dji.v5.common.error.IDJIError;
import dji.v5.manager.aircraft.virtualstick.VirtualStickManager;

/** Authenticated, expiring velocity commands. Default receiver never enables flight control. */
public final class PatrolCommandBridge {
    // USER_SETTINGS
    public static final boolean LIVE_OUTPUT_ENABLED = false; // 校正・軸・実機検証後にだけ変更する
    private static final int PORT = 5001; // 映像転送とは別の受信ポート
    private static final long WATCHDOG_MS = 300; // 指令途絶で速度ゼロ
    private static final long TICK_MS = 100; // SDK送信周期10Hz
    private static final int MAX_PACKET_BYTES = 4096; // 受信1行の上限

    public interface Status { void update(String text); }
    private final Status status;
    private volatile boolean running;
    private volatile ServerSocket server;
    private volatile Socket client;
    private ScheduledExecutorService scheduler;
    private boolean liveReady;
    private long generation;
    private long lastGood, expiry;
    private double roll, pitch, up, yaw;
    private String lastState = "STOPPED";

    public PatrolCommandBridge(Status status) { this.status = status; }
    public boolean isRunning() { return running; }

    public synchronized void start(String token) {
        if (running) return;
        if (!token.matches("[a-fA-F0-9]{64}")) throw new IllegalArgumentException("64桁のランダムhexトークンが必要");
        running = true;
        final long activeGeneration = ++generation;
        clear();
        scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(() -> { if (active(activeGeneration)) tick(); }, 0, TICK_MS, TimeUnit.MILLISECONDS);
        new Thread(() -> receive(token, activeGeneration), "patrol-receiver").start();
        if (LIVE_OUTPUT_ENABLED) {
            VirtualStickManager.getInstance().enableVirtualStick(new CommonCallbacks.CompletionCallback() {
                @Override public void onSuccess() {
                    synchronized (PatrolCommandBridge.this) {
                        if (!active(activeGeneration)) { if (!running) disable(); return; }
                        VirtualStickManager.getInstance().setVirtualStickAdvancedModeEnabled(true);
                        liveReady = true;
                    }
                }
                @Override public void onFailure(IDJIError error) {
                    synchronized (PatrolCommandBridge.this) {
                        if (active(activeGeneration)) { state("ENABLE_FAILED " + error.description()); stop(); }
                    }
                }
            });
        }
        state(LIVE_OUTPUT_ENABLED ? "LIVE_PENDING" : "DRY_RUN_WAIT");
    }

    private synchronized boolean active(long g) { return running && generation == g; }

    private void receive(String token, long g) {
        try (ServerSocket listening = new ServerSocket(PORT)) {
            synchronized (this) {
                if (!active(g)) return;
                server = listening;
            }
            while (active(g)) {
                try (Socket connection = listening.accept()) {
                    synchronized (this) {
                        if (!active(g)) return;
                        client = connection;
                        clear();
                    }
                    connection.setSoTimeout((int) WATCHDOG_MS);
                    InputStream input = connection.getInputStream();
                    long sequence = 0;
                    String session = null;
                    while (active(g)) {
                        String line;
                        try { line = readLine(input); }
                        catch (SocketTimeoutException timeout) { synchronized (this) { if (active(g)) clear(); } continue; }
                        if (line == null) break;
                        try {
                            JSONObject p = new JSONObject(line);
                            long now = System.currentTimeMillis(), until = p.getLong("expires_unix_ms");
                            long seq = p.getLong("seq");
                            String incomingSession = p.getString("session");
                            double r=p.getDouble("roll_mps"), q=p.getDouble("pitch_mps"), u=p.getDouble("up_mps"), y=p.getDouble("yaw_dps");
                            if (!PatrolCommandGate.accepts(p.getInt("version"), token, p.getString("token"),
                                session, incomingSession, sequence, seq, now, until, r, q, u, y))
                                throw new IllegalArgumentException("rejected");
                            synchronized (this) {
                                if (!active(g)) return;
                                roll=r; pitch=q; up=u; yaw=y; expiry=until; lastGood=SystemClock.elapsedRealtime();
                            }
                            sequence=seq; session=incomingSession;
                        } catch (Exception rejected) { synchronized (this) { if (active(g)) { clear(); state("PACKET_REJECTED"); } } }
                    }
                } catch (Exception connectionError) {
                    if (active(g)) state("CONNECTION_CLOSED");
                } finally { synchronized (this) { if (active(g)) { clear(); client=null; } } }
            }
        } catch (Exception error) { if (active(g)) state("RECEIVER_FAILED " + error.getClass().getSimpleName()); }
        finally { synchronized (this) { if (active(g)) stop(); } }
    }

    private String readLine(InputStream input) throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        int n;
        while ((n = input.read()) != -1) {
            if (n == '\n') return bytes.toString("UTF-8");
            if (bytes.size() >= MAX_PACKET_BYTES) throw new IllegalArgumentException("oversized packet");
            bytes.write(n);
        }
        return null;
    }

    private synchronized void tick() {
        if (!running) return;
        boolean fresh = lastGood > 0 && SystemClock.elapsedRealtime()-lastGood <= WATCHDOG_MS && System.currentTimeMillis()<expiry;
        if (!fresh) clear();
        if (liveReady) {
            try { send(roll,pitch,up,yaw); }
            catch (RuntimeException sdkError) { state("SDK_SEND_FAILED"); stop(); return; }
        }
        state((liveReady ? "LIVE_" : "DRY_RUN_") + (fresh ? "COMMAND" : "ZERO_WATCHDOG"));
    }

    private void send(double r, double p, double u, double y) {
        VirtualStickFlightControlParam value = new VirtualStickFlightControlParam();
        value.setRollPitchCoordinateSystem(FlightCoordinateSystem.BODY);
        value.setRollPitchControlMode(RollPitchControlMode.VELOCITY);
        value.setVerticalControlMode(VerticalControlMode.VELOCITY);
        value.setYawControlMode(YawControlMode.ANGULAR_VELOCITY);
        value.setRoll(r); value.setPitch(p); value.setVerticalThrottle(u); value.setYaw(y);
        VirtualStickManager.getInstance().sendVirtualStickAdvancedParam(value);
    }

    private void disable() {
        VirtualStickManager.getInstance().disableVirtualStick(new CommonCallbacks.CompletionCallback() {
            @Override public void onSuccess() { }
            @Override public void onFailure(IDJIError error) { state("DISABLE_FAILED " + error.description()); }
        });
    }

    private void clear() { roll=pitch=up=yaw=0.; lastGood=expiry=0; }
    private synchronized void state(String text) {
        if (!text.equals(lastState)) { lastState=text; status.update(text); }
    }
    public synchronized void stop() {
        running=false;
        if (liveReady) {
            liveReady=false;
            try { send(0.,0.,0.,0.); } catch (RuntimeException ignored) { }
            try { disable(); } catch (RuntimeException ignored) { state("DISABLE_FAILED"); }
        }
        clear();
        try { if (client!=null) client.close(); } catch (Exception ignored) { }
        try { if (server!=null) server.close(); } catch (Exception ignored) { }
        if (scheduler!=null) scheduler.shutdownNow();
        state("STOPPED");
    }
}
