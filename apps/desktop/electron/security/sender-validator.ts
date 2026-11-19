import type { IpcMainInvokeEvent } from 'electron';

export class SenderValidator {
  public static isTrustedSender(event: IpcMainInvokeEvent): boolean {
    const senderUrl = event.senderFrame?.url || '';

    // Allow dev server URL
    if (senderUrl.startsWith('http://localhost:5173') || senderUrl.startsWith('http://127.0.0.1:5173')) {
      return true;
    }

    // Allow production file protocol
    if (senderUrl.startsWith('file://') && senderUrl.includes('/renderer/index.html')) {
      return true;
    }

    // Block any remote web page from sending IPC messages
    return false;
  }
}
