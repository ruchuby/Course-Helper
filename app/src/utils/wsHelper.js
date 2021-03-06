import encrypt from '@/utils/encrypt'
import store from "@/store"

const cmd = {
    'js_encrypt': async (params) => encrypt(params.data, params.key),
    'update_download_progress': async (params) => {
        if ('finished' in params) {
            const res = await store.dispatch('updateDownloadProgress', {
                downloadId: params['download_id'],
                finished: true
            })
            that.sendMsg(`下载成功: ${res}`, 'success')
        } else if ('error' in params) {
            const res = await store.dispatch('updateDownloadProgress', {
                downloadId: params['download_id'],
                error: true
            })
            that.sendMsg(`下载失败: ${res}`, 'error')
        } else {
            return store.dispatch('updateDownloadProgress', {
                downloadId: params['download_id'],
                speed: params['speed'],
                timeRemain: params['time_remain'],
                downSize: params['down_size'],
                downSizeRaw: params['down_size_raw'],
            })
        }
    }
}


const that = {
    ws: null,
    lockReconnect: false, //是否正在重连
    timeout: 30 * 1000, //心跳间隔
    heartTimeId: null, //心跳倒计时
    serverHeartTimeId: null, //服务器的心跳回复倒计时，超时则关闭连接
    reconnectTimeId: null, //断开 重连倒计时

    sendMsg: null, // 用于发送消息提示
    callback: {
        connect: null,
        disconnect: null
    },

    injectCallback(connect, disconnect) {
        that.callback = {connect, disconnect}
    },
    injectMessage(sendMsg) {
        that.sendMsg = sendMsg
    },
    onopen() {
        console.log('连接成功')
        if (that.callback.connect !== null) {
            that.callback.connect()
        }
        that.start() //开启心跳
    },
    onclose() {
        console.log("连接关闭")
        if (that.callback.disconnect !== null) {
            that.callback.disconnect()
        }
        that.reconnect() //重连
    },
    async onmessage(event) {
        if (event.data !== 'heartCheck') {
            let msg = JSON.parse(event.data)
            let resData = 'ERROR'
            if ('data' in msg && 'cmd' in msg.data) {
                let data = msg.data
                if (data.cmd in cmd) {
                    try {
                        resData = await cmd[data.cmd](data.params)
                    } catch (e) {
                        console.log('消息错误', e)
                    }
                }
            }

            if (msg.reply) {
                const out = {
                    message_id: msg.message_id,
                    reply: true,
                    data: resData
                }
                that.ws.send(JSON.stringify(out))
            }
        }
        that.reset() //收到服务器信息，心跳重置
    },
    reset() {
        clearTimeout(that.heartTimeId)
        clearTimeout(that.serverHeartTimeId)
        that.start(); //启动下一次心跳
    },
    connect() {
        that.ws = new WebSocket('ws://localhost:6498/websocket/connect/course-helper')
        that.ws.onopen = that.onopen
        that.ws.onmessage = that.onmessage
        that.ws.onclose = that.onclose
    },
    start() {
        // 存在两种心跳计时则清空
        that.heartTimeId && clearTimeout(that.heartTimeId);
        that.serverHeartTimeId && clearTimeout(that.serverHeartTimeId);

        that.heartTimeId = setTimeout(() => {
            if (that.ws.readyState === 1) { //若连接正常则发送心跳包
                that.ws.send('"heartCheck"')
            } else { //否则重连
                that.reconnect()
            }

            // 服务器心跳回复超时则关闭连接
            that.serverHeartTimeId = setTimeout(() => that.ws.close(), that.timeout);
        }, that.timeout)
    },
    reconnect() {
        if (that.lockReconnect) return
        that.lockReconnect = true // 正在尝试重连
        console.log('2s后尝试重连')
        //设置延迟5s再尝试重连，避免重复请求重连
        that.reconnectTimeId && clearTimeout(that.reconnectTimeId);
        that.reconnectTimeId = setTimeout(() => {
            that.connect();//新连接
            that.lockReconnect = false;
        }, 2000)
    }
}


export default that
