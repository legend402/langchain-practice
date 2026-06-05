import forge from "node-forge";
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
  publicKey: forge.pki.rsa.PublicKey;
  expires_at: number;
}

let cache: PublicKeyCache | null = null;

/**
 * 从后端获取 RSA 公钥并解析为 forge 公钥对象
 *
 * 公钥在内存中缓存，过期前 5 分钟自动刷新。
 * 使用 httpClient.raw() 发起请求，复用已有的 URL 解析逻辑。
 *
 * @returns 包含 key_id、forge 公钥对象和过期时间戳的缓存对象
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

  const publicKey = forge.pki.publicKeyFromPem(data.public_key) as forge.pki.rsa.PublicKey;

  cache = {
    key_id: data.key_id,
    publicKey,
    expires_at: new Date(data.expires_at).getTime(),
  };
  return cache;
}

/**
 * 使用 RSA-OAEP (SHA-256) 加密密码
 *
 * 从后端获取公钥（带内存缓存），使用 node-forge 进行 RSA-OAEP 加密。
 * 加密结果为 base64 编码的密文字符串。
 * 不依赖 Web Crypto API，在 HTTP 环境下也可正常工作。
 *
 * @param password - 待加密的明文密码
 * @returns encrypted: base64 编码的 RSA 密文；key_id: 对应的公钥标识，后端用于查找私钥解密
 */
export async function encryptPassword(
  password: string,
): Promise<{ encrypted: string; key_id: string }> {
  const { key_id, publicKey } = await fetchPublicKey();
  const encryptedBytes = publicKey.encrypt(password, "RSA-OAEP", {
    md: forge.md.sha256.create(),
  });
  const encrypted = forge.util.encode64(encryptedBytes);
  return { encrypted, key_id };
}
