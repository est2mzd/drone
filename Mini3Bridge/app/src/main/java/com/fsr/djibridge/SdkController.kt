package com.fsr.djibridge

import android.util.Log
import dji.sdk.keyvalue.key.FlightControllerKey
import dji.sdk.keyvalue.key.ProductKey
import androidx.fragment.app.FragmentActivity
import dji.v5.common.callback.CommonCallbacks
import dji.v5.common.error.IDJIError
import dji.v5.common.register.DJISDKInitEvent
import dji.v5.et.create
import dji.v5.et.listen
import dji.v5.manager.SDKManager
import dji.v5.manager.account.LoginState
import dji.v5.manager.account.UserAccountManager
import dji.v5.manager.interfaces.SDKManagerCallback
import dji.v5.network.DJINetworkManager

object SdkController {
    private const val TAG = "Mini3Bridge"
    private var keysListening = false

    fun start(app: BridgeApplication) {
        SDKManager.getInstance().init(app, object : SDKManagerCallback {
            override fun onRegisterSuccess() {
                app.state.registered = true
                app.state.registerError = null
                Log.i(TAG, "register success")
                listenKeys(app)
                app.state.publish()
            }

            override fun onRegisterFailure(error: IDJIError) {
                app.state.registered = false
                app.state.registerError = "${error.errorCode()} ${error.description()}"
                Log.e(TAG, "register failure ${app.state.registerError}")
                app.state.publish()
            }

            override fun onProductDisconnect(productId: Int) {
                app.state.productConnected = false
                app.state.productId = productId
                Log.i(TAG, "product disconnect $productId")
                app.state.publish()
            }

            override fun onProductConnect(productId: Int) {
                app.state.productConnected = true
                app.state.productId = productId
                Log.i(TAG, "product connect $productId")
                app.state.publish()
            }

            override fun onProductChanged(productId: Int) {
                app.state.productId = productId
                Log.i(TAG, "product changed $productId")
                app.state.publish()
            }

            override fun onInitProcess(event: DJISDKInitEvent, totalProcess: Int) {
                Log.i(TAG, "init $event $totalProcess")
                app.state.initEvent = event.name
                if (event == DJISDKInitEvent.INITIALIZE_COMPLETE) {
                    app.sdkInitComplete = true
                    SDKManager.getInstance().registerApp()
                }
                app.state.publish()
            }

            override fun onDatabaseDownloadProgress(current: Long, total: Long) {
                Log.i(TAG, "db $current/$total")
            }
        })

        UserAccountManager.getInstance().addLoginInfoUpdateListener { info ->
            app.state.loginState = info?.loginState?.name ?: ""
            Log.i(TAG, "login state ${app.state.loginState}")
            app.state.publish()
        }
        refreshLogin(app)

        DJINetworkManager.getInstance().addNetworkStatusListener { available ->
            Log.i(TAG, "network available=$available")
            if (app.sdkInitComplete && available && !SDKManager.getInstance().isRegistered) {
                SDKManager.getInstance().registerApp()
            }
        }
    }

    fun refreshLogin(app: BridgeApplication) {
        val state = runCatching { UserAccountManager.getInstance().loginInfo?.loginState }.getOrNull()
        app.state.loginState = state?.name ?: ""
    }

    fun login(activity: FragmentActivity) {
        val email = BuildConfig.DJI_EMAIL
        val password = BuildConfig.DJI_PASSWORD
        val callback = object : CommonCallbacks.CompletionCallback {
            override fun onSuccess() {
                Log.i(TAG, "login success")
                refreshLogin(BridgeApplication.instance)
                BridgeApplication.instance.state.publish()
            }

            override fun onFailure(error: IDJIError) {
                Log.e(TAG, "login failure ${error.errorCode()} ${error.description()}")
                BridgeApplication.instance.state.loginState = "失敗 ${error.description()}"
                BridgeApplication.instance.state.publish()
            }
        }
        if (email.isNotBlank() && password.isNotBlank()) {
            UserAccountManager.getInstance().logInDJIUserAccount(email, password, null, callback)
            return
        }
        UserAccountManager.getInstance().logInDJIUserAccount(activity, false, callback)
    }

    fun isLoggedIn(): Boolean {
        return UserAccountManager.getInstance().loginInfo?.loginState == LoginState.LOGGED_IN
    }

    private fun listenKeys(app: BridgeApplication) {
        if (keysListening) {
            return
        }
        keysListening = true
        FlightControllerKey.KeyConnection.create().listen(app) { connected ->
            app.state.fcConnected = connected == true
            Log.i(TAG, "fc connected=$connected")
            app.state.publish()
        }
        ProductKey.KeyProductType.create().listen(app) { type ->
            app.state.productType = type?.name ?: ""
            Log.i(TAG, "product type=$type")
            app.state.publish()
        }
    }
}
