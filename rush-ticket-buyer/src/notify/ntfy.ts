import { request } from 'undici';
import type { Notifier, Alert } from '../types.js';

/**
 * ntfy.sh notifier — simplest possible mobile push (no account needed).
 * Subscribe to your topic in the ntfy app; alerts arrive with a tap-through link.
 */
export class NtfyNotifier implements Notifier {
  readonly name = 'ntfy';

  constructor(
    private topic: string,
    private server = process.env.NTFY_SERVER ?? 'https://ntfy.sh',
  ) {}

  async send(alert: Alert): Promise<void> {
    await request(`${this.server}/${this.topic}`, {
      method: 'POST',
      headers: {
        Title: alert.title,
        Click: alert.url, // tap the notification -> straight to the listing
        Priority: 'high',
        Tags: 'tickets',
      },
      body: alert.body,
    });
  }
}
