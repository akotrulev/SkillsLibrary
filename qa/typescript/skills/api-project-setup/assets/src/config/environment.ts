const DEFAULTS: Readonly<Record<string, string>> = {
  API_BASE_URL: 'http://localhost:8080',
};

export function requiredEnv(name: string): string {
  const value = process.env[name] || DEFAULTS[name];
  if (!value) {
    throw new Error(`Missing setting ${name}: export it, or set it in the CI secret store`);
  }
  return value;
}

export function getTestEnvironment() {
  return { apiUri: requiredEnv('API_BASE_URL') } as const;
}
