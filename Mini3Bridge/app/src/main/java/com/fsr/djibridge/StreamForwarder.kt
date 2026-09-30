package com.fsr.djibridge

import android.content.Context
import android.util.Log
import dji.sdk.keyvalue.value.common.ComponentIndexType
import dji.v5.manager.datacenter.MediaDataCenter
import dji.v5.manager.interfaces.ICameraStreamManager
import java.io.File
import java.io.FileOutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread

class StreamForwarder(
    context: Context,
    private val onStatus: (String) -> Unit,
    private val onStats: (String) -> Unit,
) {
    private val appContext = context.applicationContext
    private val running = AtomicBoolean(false)
    private val queue = LinkedBlockingQueue<ByteArray>(8)
    private var socket: Socket? = null
    private var worker: Thread? = null
    private var cameraIndex: ComponentIndexType? = null
    private var lastMime = ""
    private var lastWidth = 0
    private var lastHeight = 0
    private var dump: FileOutputStream? = null
    private var dumpUntil = 0L

    @Volatile var sentBytes: Long = 0
    @Volatile var sentChunks: Long = 0
    @Volatile var mime: String = ""
    @Volatile var width: Int = 0
    @Volatile var height: Int = 0
    @Volatile var queueDepth: Int = 0
    @Volatile var lastError: String = ""
    @Volatile var statusLine: String = "停止"

    private val cameraListener = object : ICameraStreamManager.AvailableCameraUpdatedListener {
        override fun onAvailableCameraUpdated(availableCameraList: MutableList<ComponentIndexType>) {
            val next = availableCameraList.firstOrNull { it == ComponentIndexType.LEFT_OR_MAIN }
                ?: availableCameraList.firstOrNull()
            Log.i(TAG, "cameras=$availableCameraList pick=$next")
            if (next == cameraIndex) {
                return
            }
            swapCamera(next)
        }

        override fun onCameraStreamEnableUpdate(cameraStreamEnableMap: MutableMap<ComponentIndexType, Boolean>) {
            Log.i(TAG, "stream enable=$cameraStreamEnableMap")
        }
    }

    private val streamListener = ICameraStreamManager.ReceiveStreamListener { data, offset, length, info ->
        if (!running.get() || length <= 0) {
            return@ReceiveStreamListener
        }
        val mimeName = info.mimeType?.name ?: "UNKNOWN"
        val frameWidth = info.width
        val frameHeight = info.height
        val copy = data.copyOfRange(offset, offset + length)
        if (sentChunks == 0L) {
            val n = minOf(16, copy.size)
            val hex = copy.copyOfRange(0, n).joinToString("") { "%02x".format(it) }
            Log.i(TAG, "first bytes $hex mime=$mimeName ${frameWidth}x$frameHeight len=$length")
        }
        maybeSendCodec(mimeName, frameWidth, frameHeight)
        writeDump(copy)
        val packet = frame(TYPE_CHUNK, copy)
        if (!queue.offer(packet)) {
            queue.clear()
            queue.offer(packet)
        }
        sentChunks += 1
        queueDepth = queue.size
    }

    fun start(host: String, port: Int) {
        if (!running.compareAndSet(false, true)) {
            return
        }
        sentBytes = 0
        sentChunks = 0
        lastError = ""
        lastMime = ""
        openDump()
        status("PC へ接続中 $host:$port")
        worker = thread(name = "stream-forward") {
            try {
                val sock = Socket()
                sock.tcpNoDelay = true
                sock.sendBufferSize = 64 * 1024
                sock.connect(InetSocketAddress(host, port), 5000)
                sock.keepAlive = true
                socket = sock
                status("PC 接続済み。映像待ち")
                val out = sock.getOutputStream()
                val cameras = MediaDataCenter.getInstance().cameraStreamManager
                cameras.addAvailableCameraUpdatedListener(cameraListener)
                while (running.get()) {
                    val packet = queue.poll(200, java.util.concurrent.TimeUnit.MILLISECONDS) ?: continue
                    out.write(packet)
                    out.flush()
                    sentBytes += packet.size.toLong()
                    queueDepth = queue.size
                }
            } catch (e: Exception) {
                lastError = e.message ?: e.javaClass.simpleName
                Log.e(TAG, "forward failed", e)
                status("転送失敗: $lastError")
            } finally {
                detachCamera()
                runCatching {
                    MediaDataCenter.getInstance().cameraStreamManager
                        .removeAvailableCameraUpdatedListener(cameraListener)
                }
                runCatching { socket?.close() }
                socket = null
                closeDump()
                running.set(false)
                publishStats()
            }
        }
    }

    fun stop() {
        running.set(false)
        worker?.join(2000)
        worker = null
        status("転送停止")
    }

    fun isRunning(): Boolean = running.get()

    fun publishStats() {
        val kbps = sentBytes / 1024
        onStats(
            "mime=$mime ${width}x$height\n" +
                "chunks=$sentChunks sent=${kbps}KiB queue=$queueDepth\n" +
                "dump=${dumpFile().absolutePath}\n" +
                lastError
        )
    }

    private fun swapCamera(next: ComponentIndexType?) {
        detachCamera()
        cameraIndex = next
        if (next == null) {
            status("カメラ無し")
            return
        }
        MediaDataCenter.getInstance().cameraStreamManager.addReceiveStreamListener(next, streamListener)
        status("カメラ $next の圧縮映像を転送中")
    }

    private fun detachCamera() {
        val current = cameraIndex ?: return
        runCatching {
            MediaDataCenter.getInstance().cameraStreamManager.removeReceiveStreamListener(streamListener)
        }
        Log.i(TAG, "detach $current")
        cameraIndex = null
    }

    private fun maybeSendCodec(mimeName: String, frameWidth: Int, frameHeight: Int) {
        mime = mimeName
        width = frameWidth
        height = frameHeight
        if (mimeName == lastMime && frameWidth == lastWidth && frameHeight == lastHeight) {
            return
        }
        lastMime = mimeName
        lastWidth = frameWidth
        lastHeight = frameHeight
        val mimeBytes = mimeName.toByteArray(Charsets.UTF_8)
        val payload = ByteBuffer.allocate(1 + mimeBytes.size + 4).order(ByteOrder.BIG_ENDIAN)
        payload.put(mimeBytes.size.toByte())
        payload.put(mimeBytes)
        payload.putShort(frameWidth.toShort())
        payload.putShort(frameHeight.toShort())
        queue.offer(frame(TYPE_CODEC, payload.array()))
        Log.i(TAG, "codec $mimeName ${frameWidth}x$frameHeight")
    }

    private fun openDump() {
        closeDump()
        val file = dumpFile()
        dump = FileOutputStream(file, false)
        dumpUntil = android.os.SystemClock.elapsedRealtime() + 5_000
        Log.i(TAG, "dump ${file.absolutePath}")
    }

    private fun writeDump(copy: ByteArray) {
        val out = dump ?: return
        if (android.os.SystemClock.elapsedRealtime() > dumpUntil) {
            closeDump()
            return
        }
        runCatching { out.write(copy) }
    }

    private fun closeDump() {
        runCatching { dump?.flush() }
        runCatching { dump?.close() }
        dump = null
    }

    private fun dumpFile(): File = File(appContext.filesDir, "live_dump.bin")

    private fun status(text: String) {
        statusLine = text
        Log.i(TAG, text)
        onStatus(text)
    }

    private fun frame(type: Int, payload: ByteArray): ByteArray {
        val bodyLen = 1 + payload.size
        val out = ByteBuffer.allocate(4 + bodyLen).order(ByteOrder.BIG_ENDIAN)
        out.putInt(bodyLen)
        out.put(type.toByte())
        out.put(payload)
        return out.array()
    }

    companion object {
        private const val TAG = "Mini3Bridge"
        private const val TYPE_CODEC = 1
        private const val TYPE_CHUNK = 2
    }
}
