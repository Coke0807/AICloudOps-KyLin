#!/bin/sh

# 更新配置
/update-config.sh /public/_app.config.js

# 启动静态服务器
exec static-web-server
