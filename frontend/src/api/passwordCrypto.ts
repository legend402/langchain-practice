import { httpClient } from "./client";

const PUBLIC_KEY_URL = "/api/v1/auth/public-key";
const REFRESH_AHEAD_MS = 5 * 60 * 1000;

interface PublicKeyResponse {
  key_id: string;
  public_key: string;
  expires_at: string;
}

interface PublicKeyCache {
  key_id: string;
  cryptoKey: CryptoKey;
  expires_at: number;
}

let cache: PublicKeyCache | null = null;

/**
 * 将 PEM 格式的公钥字符串转换为 ArrayBuffer
 *
 * @param pem - PEM 格式的公钥字符串（含 BEGIN/END PUBLIC KEY 标记）
 * @returns 解码后的 ArrayBuffer
 */
function pemToArrayBuffer(pem: string): ArrayBuffer {
  const b64 = pem
    .replace(/-----BEGIN PUBLIC KEY-----/, "")
    .replace(/-----END PUBLIC KEY-----/, "")
    .replace(/\s/g, "");
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * 从后端获取 RSA 公钥并导入为 CryptoKey
 *
 * 公钥在内存中缓存，过期前 5 分钟自动刷新。
 * 使用 httpClient.raw() 发起请求，复用已有的 URL 解析逻辑。
 *
 * @returns 包含 key_id、CryptoKey 和过期时间戳的缓存对象
 * @throws 获取公钥失败时抛出错误
 */
async function fetchPublicKey(): Promise<PublicKeyCache> {
  if (cache && Date.now() < cache.expires_at - REFRESH_AHEAD_MS) {
    return cache;
  }

  const res = await httpClient.raw(PUBLIC_KEY_URL);
  if (!res.ok) {
    throw new Error("获取公钥失败，请刷新页面重试");
  }
  const body = await res.json();
  const data: PublicKeyResponse = body.result ?? body;

  const cryptoKey = await crypto.subtle.importKey(
    "spki",
    pemToArrayBuffer(data.public_key),
    { name: "RSA-OAEP", hash: "SHA-256" },
    false,
    ["encrypt"],
  );

  cache = {
    key_id: data.key_id,
    cryptoKey,
    expires_at: new Date(data.expires_at).getTime(),
  };
  return cache;
}

/**
 * 使用 RSA-OAEP 加密密码
 *
 * 从后端获取公钥（带内存缓存），使用 Web Crypto API 进行 RSA-OAEP 加密。
 * 加密结果为 base64 编码的密文字符串。
 *
 * @param password - 待加密的明文密码
 * @returns encrypted: base64 编码的 RSA 密文；key_id: 对应的公钥标识，后端用于查找私钥解密
 */
export async function encryptPassword(
  password: string,
): Promise<{ encrypted: string; key_id: string }> {
  const { key_id, cryptoKey } = await fetchPublicKey();
  const encoded = new TextEncoder().encode(password);
  const cipherBuffer = await crypto.subtle.encrypt(
    { name: "RSA-OAEP" },
    cryptoKey,
    encoded,
  );
  const encrypted = btoa(
    String.fromCharCode(...new Uint8Array(cipherBuffer)),
  );
  return { encrypted, key_id };
}
