export function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing env var ${name}: set it in the shell or the CI secret store`);
  }
  return value;
}
