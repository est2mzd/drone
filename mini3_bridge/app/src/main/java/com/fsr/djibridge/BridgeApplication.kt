package com.fsr.djibridge

import android.app.Application
import android.content.Context
import android.os.Handler
import android.os.Looper

class BridgeApplication : Application() {
    val state = SdkState()
    val main = Handler(Looper.getMainLooper())

    @Volatile
    var sdkInitComplete = false

    override fun attachBaseContext(base: Context) {
        super.attachBaseContext(base)
        com.cySdkyc.clx.Helper.install(this)
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        if (!BuildConfig.API_KEY_PRESENT) {
            state.registerError = "API_KEY が gradle.properties に無い"
            state.publish()
        }
        SdkController.start(this)
    }

    class SdkState {
        @Volatile var registered: Boolean = false
        @Volatile var registerError: String? = null
        @Volatile var initEvent: String = ""
        @Volatile var productConnected: Boolean = false
        @Volatile var productId: Int = -1
        @Volatile var fcConnected: Boolean = false
        @Volatile var productType: String = ""
        @Volatile var loginState: String = ""
        @Volatile var usbPermission: String = ""

        private val listeners = java.util.concurrent.CopyOnWriteArrayList<() -> Unit>()

        fun publish() {
            instance.main.post {
                listeners.forEach { it.invoke() }
            }
        }

        fun observe(listener: () -> Unit) {
            listeners.add(listener)
            listener.invoke()
        }

        fun remove(listener: () -> Unit) {
            listeners.remove(listener)
        }
    }

    companion object {
        lateinit var instance: BridgeApplication
            private set
    }
}
