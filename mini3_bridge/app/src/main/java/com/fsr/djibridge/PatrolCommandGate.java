package com.fsr.djibridge;

/** Pure validation separated from Android and the aircraft SDK for host testing. */
public final class PatrolCommandGate {
    // USER_SETTINGS
    private static final long MAX_TTL_MS = 300; // 最大有効時間
    private static final double MAX_SPEED_MPS = 0.25; // 3軸の速度ノルムの上限
    private static final double MAX_YAW_DPS = 10.0; // yaw角速度上限

    public static boolean accepts(int version, String expectedToken, String token,
        String previousSession, String session, long previousSeq, long seq,
        long nowMs, long expiresMs, double roll, double pitch, double up, double yaw) {
        return version == 1 && expectedToken != null && expectedToken.equals(token) &&
            session != null && session.matches("[a-fA-F0-9]{32}") &&
            (previousSession == null || previousSession.equals(session)) && seq > previousSeq &&
            expiresMs > nowMs && expiresMs-nowMs <= MAX_TTL_MS &&
            Double.isFinite(roll) && Double.isFinite(pitch) && Double.isFinite(up) && Double.isFinite(yaw) &&
            Math.sqrt(roll*roll+pitch*pitch+up*up) <= MAX_SPEED_MPS && Math.abs(yaw) <= MAX_YAW_DPS;
    }

    private PatrolCommandGate() { }
}
