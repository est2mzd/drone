package com.fsr.djibridge

import android.Manifest
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.hardware.usb.UsbManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.WindowManager
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {
    private lateinit var statusText: TextView
    private lateinit var statsText: TextView
    private lateinit var hostInput: EditText
    private lateinit var portInput: EditText
    private lateinit var toggleButton: Button
    private lateinit var loginButton: Button
    private lateinit var usbButton: Button
    private lateinit var forwarder: StreamForwarder
    private val main = Handler(Looper.getMainLooper())
    private lateinit var patrol: PatrolCommandBridge
    private var autoStart = false
    private var autoStarted = false
    private var loginPrompted = false

    private val usbReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != USB_PERMISSION) {
                return
            }
            val granted = intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)
            Log.i(TAG, "usb permission granted=$granted")
            BridgeApplication.instance.state.usbPermission = if (granted) "許可済み" else "拒否"
            BridgeApplication.instance.state.publish()
        }
    }

    private val refresh = object : Runnable {
        override fun run() {
            render()
            val state = BridgeApplication.instance.state
            if (state.registered && !loginPrompted && !SdkController.isLoggedIn()) {
                loginPrompted = true
                SdkController.login(this@MainActivity)
            }
            if (autoStart && !autoStarted && state.registered) {
                autoStarted = true
                startForward()
            }
            main.postDelayed(this, 500)
        }
    }

    private val onState = { render() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        statusText = findViewById(R.id.statusText)
        statsText = findViewById(R.id.statsText)
        hostInput = findViewById(R.id.hostInput)
        portInput = findViewById(R.id.portInput)
        toggleButton = findViewById(R.id.toggleButton)
        loginButton = findViewById(R.id.loginButton)
        usbButton = findViewById(R.id.usbButton)
        forwarder = StreamForwarder(this, onStatus = { main.post { statusText.append("\n$it") } }, onStats = { })
        ContextCompat.registerReceiver(
            this,
            usbReceiver,
            IntentFilter(USB_PERMISSION),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )

        intent.getStringExtra("host")?.let { hostInput.setText(it) }
        if (intent.hasExtra("port")) {
            portInput.setText(intent.getIntExtra("port", 5000).toString())
        }
        autoStart = intent.getBooleanExtra("auto", false)

        loginButton.setOnClickListener { SdkController.login(this) }
        usbButton.setOnClickListener { requestUsbAccessory(showDialog = true) }
        toggleButton.setOnClickListener {
            if (forwarder.isRunning()) {
                forwarder.stop()
            } else {
                startForward()
            }
            render()
        }
        val patrolStatus = findViewById<TextView>(R.id.patrolStatusText)
        val patrolToken = findViewById<EditText>(R.id.patrolTokenInput)
        val patrolButton = findViewById<Button>(R.id.patrolButton)
        patrol = PatrolCommandBridge { message -> main.post { patrolStatus.text = message } }
        patrolButton.setOnClickListener {
            if (patrol.isRunning) {
                patrol.stop()
            } else if (PatrolCommandBridge.LIVE_OUTPUT_ENABLED) {
                val state = BridgeApplication.instance.state
                if (!state.registered || !state.fcConnected || state.productType != "DJI_MINI_3") {
                    patrolStatus.text = "Mini 3の接続を確認してください"
                } else {
                    androidx.appcompat.app.AlertDialog.Builder(this)
                        .setMessage("実機への速度指令を有効にします。尺度・ジンバル固定・機体座標軸・障害物観測の実機検証が完了していますか？")
                        .setPositiveButton("検証済み・有効化") { _, _ ->
                            try { patrol.start(patrolToken.text.toString().trim()) }
                            catch (e: IllegalArgumentException) { patrolStatus.text = e.message }
                        }
                        .setNegativeButton("キャンセル", null).show()
                }
            } else {
                try { patrol.start(patrolToken.text.toString().trim()) }
                catch (e: IllegalArgumentException) { patrolStatus.text = e.message }
            }
        }
        BridgeApplication.instance.state.observe(onState)
        ensurePermissions()
    }

    override fun onResume() {
        super.onResume()
        requestUsbAccessory(showDialog = false)
        main.post(refresh)
    }

    override fun onPause() {
        if (::patrol.isInitialized) patrol.stop()
        main.removeCallbacks(refresh)
        super.onPause()
    }

    override fun onDestroy() {
        unregisterReceiver(usbReceiver)
        BridgeApplication.instance.state.remove(onState)
        if (isFinishing) {
            forwarder.stop()
        }
        super.onDestroy()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (BridgeApplication.instance.sdkInitComplete && !BridgeApplication.instance.state.registered) {
            dji.v5.manager.SDKManager.getInstance().registerApp()
        }
    }

    private fun startForward() {
        val host = hostInput.text.toString().trim()
        val port = portInput.text.toString().trim().toIntOrNull()
        if (host.isEmpty() || port == null) {
            statusText.append("\nアドレスが不正")
            return
        }
        hostInput.isEnabled = false
        portInput.isEnabled = false
        forwarder.start(host, port)
    }

    private fun render() {
        val state = BridgeApplication.instance.state
        val register = when {
            state.registered -> "登録成功"
            state.registerError != null -> "登録失敗 ${state.registerError}"
            else -> "登録待ち ${state.initEvent}"
        }
        val product = if (state.productConnected) "接続 id=${state.productId}" else "未接続"
        val fc = if (state.fcConnected) "接続" else "未接続"
        val type = if (state.productType.isEmpty()) "-" else state.productType
        val login = if (state.loginState.isEmpty()) "-" else state.loginState
        val usb = if (state.usbPermission.isEmpty()) "-" else state.usbPermission
        statusText.text = "SDK: $register\nアカウント: $login\nUSB: $usb\n機体: $product\nFC: $fc\n機種: $type\n転送: ${forwarder.statusLine}"
        forwarder.publishStats()
        statsText.text = statsSnapshot()
        toggleButton.text = getString(if (forwarder.isRunning()) R.string.stop else R.string.start)
        val editing = !forwarder.isRunning()
        hostInput.isEnabled = editing
        portInput.isEnabled = editing
    }

    private fun statsSnapshot(): String {
        return "mime=${forwarder.mime} ${forwarder.width}x${forwarder.height}\n" +
            "chunks=${forwarder.sentChunks} sent=${forwarder.sentBytes / 1024}KiB queue=${forwarder.queueDepth}\n" +
            forwarder.lastError
    }

    private fun requestUsbAccessory(showDialog: Boolean) {
        val usb = getSystemService(UsbManager::class.java) ?: return
        val accessory = usb.accessoryList?.firstOrNull()
        val state = BridgeApplication.instance.state
        if (accessory == null) {
            state.usbPermission = "アクセサリなし"
            state.publish()
            return
        }
        if (usb.hasPermission(accessory)) {
            state.usbPermission = "許可済み"
            state.publish()
            return
        }
        state.usbPermission = "未許可"
        state.publish()
        if (!showDialog) {
            return
        }
        Log.i(TAG, "request usb permission model=${accessory.model}")
        val pending = PendingIntent.getBroadcast(
            this,
            0,
            Intent(USB_PERMISSION).setPackage(packageName),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE,
        )
        usb.requestPermission(accessory, pending)
    }

    private fun ensurePermissions() {
        val needed = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.READ_PHONE_STATE,
        ).filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), 1)
        }
    }

    companion object {
        private const val TAG = "mini3_bridge"
        private const val USB_PERMISSION = "com.fsr.djibridge.USB_PERMISSION"
    }
}
