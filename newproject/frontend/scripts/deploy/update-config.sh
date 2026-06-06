#!/bin/sh

# 检查是否提供了目标文件路径
if [ -z "$1" ]; then
    echo "Error: Please provide the target config file path"
    exit 1
fi

TARGET_FILE="$1"

# 检查文件是否存在
if [ ! -f "$TARGET_FILE" ]; then
    echo "Error: File $TARGET_FILE does not exist"
    exit 1
fi

# 提取原有配置
ORIGINAL_CONFIG=$(grep -o 'window\._VBEN_ADMIN_PRO_APP_CONF_\s*=\s*{[^}]*}' "$TARGET_FILE" | sed 's/window\._VBEN_ADMIN_PRO_APP_CONF_\s*=\s*//')

# 如果没有找到原有配置，使用空对象
if [ -z "$ORIGINAL_CONFIG" ]; then
    ORIGINAL_CONFIG="{}"
fi

# 创建临时JSON文件
TMP_JSON=$(mktemp)
trap 'rm -f "$TMP_JSON"' EXIT

# 将原有配置写入临时文件
echo "$ORIGINAL_CONFIG" > "$TMP_JSON"

# 使用jq更新配置
for var in $(env | grep '^VITE_GLOB_'); do
    name=$(echo "$var" | cut -d'=' -f1)
    value=$(echo "$var" | cut -d'=' -f2-)
    
    if [ -n "$value" ]; then
        # 使用jq更新JSON，它会自动处理转义
        ORIGINAL_CONFIG=$(echo "$ORIGINAL_CONFIG" | jq --arg key "$name" --arg val "$value" '. + {($key): $val}')
    fi
done

# 构建完整的配置字符串
FULL_CONFIG="window._VBEN_ADMIN_PRO_APP_CONF_=${ORIGINAL_CONFIG};Object.freeze(window._VBEN_ADMIN_PRO_APP_CONF_);Object.defineProperty(window,\"_VBEN_ADMIN_PRO_APP_CONF_\",{configurable:false,writable:false,});"

# 更新文件
echo "$FULL_CONFIG" > "$TARGET_FILE"

echo "Configuration updated successfully"