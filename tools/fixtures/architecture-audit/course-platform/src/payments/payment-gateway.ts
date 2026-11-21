import type { PaymentsClient } from '@acme/payments-sdk';

export type ChargeRequest = {
  readonly learnerId: string;
  readonly amountCents: number;
  readonly idempotencyKey: string;
};

export type ChargeResult =
  | { readonly status: 'paid'; readonly reference: string }
  | { readonly status: 'declined' };

export class PaymentGateway {
  constructor(private readonly client: PaymentsClient) {}

  async charge(request: ChargeRequest): Promise<ChargeResult> {
    const charge = await this.client.charges.create({
      customer: request.learnerId,
      amount: request.amountCents,
      currency: 'eur',
      idempotencyKey: request.idempotencyKey,
    });
    return charge.status === 'succeeded'
      ? { status: 'paid', reference: charge.id }
      : { status: 'declined' };
  }
}
