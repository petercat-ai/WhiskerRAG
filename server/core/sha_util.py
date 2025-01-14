import hashlib


def calculate_sha256(text):
    # 将文本转换为 UTF-8 编码的字节
    text_bytes = text.encode("utf-8")

    # 创建 SHA-256 哈希对象
    sha256_hash = hashlib.sha256()

    # 更新哈希对象
    sha256_hash.update(text_bytes)

    # 返回十六进制形式的哈希值
    return sha256_hash.hexdigest()
