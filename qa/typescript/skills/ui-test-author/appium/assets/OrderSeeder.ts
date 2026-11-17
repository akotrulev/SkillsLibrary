import { strict as assert } from 'node:assert';
import { requiredEnv } from './env.js';

export type SeededOrder = {
  readonly id: string;
  readonly number: string;
  readonly title: string;
};

export class OrderSeeder {
  private readonly baseUrl = requiredEnv('API_BASE_URL');
  private readonly token = requiredEnv('API_TOKEN');
  private readonly created: string[] = [];

  async create(title: string): Promise<SeededOrder> {
    const response = await fetch(`${this.baseUrl}/api/orders`, {
      method: 'POST',
      headers: { authorization: `Bearer ${this.token}`, 'content-type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    const body = await response.text();
    assert.equal(response.status, 201, `create order "${title}": ${body}`);
    const order: { id: string; number: string } = JSON.parse(body);
    this.created.push(order.id);
    return { id: order.id, number: order.number, title };
  }

  async deleteCreated(): Promise<void> {
    for (const id of this.created.splice(0)) {
      const response = await fetch(`${this.baseUrl}/api/orders/${id}`, {
        method: 'DELETE',
        headers: { authorization: `Bearer ${this.token}` },
      });
      assert.equal(response.status, 204, `delete order ${id}: ${await response.text()}`);
    }
  }
}
