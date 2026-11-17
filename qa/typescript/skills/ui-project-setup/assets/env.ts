const DEFAULTS: Readonly<Record<string, string>> = {
  BASE_URL: 'http://localhost:3000',
};

export function requiredEnv(name: string): string {
  const value = process.env[name] || DEFAULTS[name];
  if (!value) {
    throw new Error(`Missing setting ${name}: export it, or set it in the CI secret store`);
  }
  return value;
}
