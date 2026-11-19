import { safeStorage, app } from 'electron';
import path from 'path';
import fs from 'fs';

export class SecretStorage {
  private filePath: string;
  private secrets: Record<string, string> = {}; // key -> encrypted hex string

  constructor() {
    const userData = app?.getPath ? app.getPath('userData') : process.cwd();
    this.filePath = path.join(userData, 'secure_credentials.dat');
    this.load();
  }

  private load() {
    try {
      if (fs.existsSync(this.filePath)) {
        const raw = fs.readFileSync(this.filePath, 'utf-8');
        this.secrets = JSON.parse(raw);
      }
    } catch (e) {
      this.secrets = {};
    }
  }

  private save() {
    try {
      fs.writeFileSync(this.filePath, JSON.stringify(this.secrets, null, 2), 'utf-8');
    } catch (e) {
      console.warn('Failed to save secure credentials:', e);
    }
  }

  public setSecret(key: string, value: string): void {
    if (safeStorage.isEncryptionAvailable()) {
      const encrypted = safeStorage.encryptString(value);
      this.secrets[key] = encrypted.toString('hex');
    } else {
      // Fallback base64 obfuscation if OS encryption unavailable in dev
      this.secrets[key] = Buffer.from(value, 'utf-8').toString('base64');
    }
    this.save();
  }

  public getSecret(key: string): string | null {
    const encVal = this.secrets[key];
    if (!encVal) return null;

    try {
      if (safeStorage.isEncryptionAvailable()) {
        const buf = Buffer.from(encVal, 'hex');
        return safeStorage.decryptString(buf);
      } else {
        return Buffer.from(encVal, 'base64').toString('utf-8');
      }
    } catch (e) {
      console.warn(`Failed to decrypt secret '${key}':`, e);
      return null;
    }
  }

  public removeSecret(key: string): void {
    delete this.secrets[key];
    this.save();
  }
}
