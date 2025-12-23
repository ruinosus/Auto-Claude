import fs from 'fs/promises';
import path from 'path';
import os from 'os';

/**
 * Read .env file and parse key-value pairs
 */
export async function readEnvFile(envPath: string): Promise<Record<string, string>> {
  try {
    const content = await fs.readFile(envPath, 'utf-8');
    const vars: Record<string, string> = {};

    content.split('\n').forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=');
        if (key && valueParts.length > 0) {
          vars[key.trim()] = valueParts.join('=').trim();
        }
      }
    });

    return vars;
  } catch (error) {
    // File doesn't exist yet
    return {};
  }
}

/**
 * Write env vars to .env file
 */
export async function writeEnvFile(envPath: string, vars: Record<string, string>): Promise<void> {
  const lines = Object.entries(vars)
    .filter(([key, value]) => value !== undefined && value !== '')
    .map(([key, value]) => `${key}=${value}`);

  await fs.mkdir(path.dirname(envPath), { recursive: true });
  await fs.writeFile(envPath, lines.join('\n') + '\n', 'utf-8');
}

/**
 * Update specific env vars in .env file
 */
export async function updateEnvVars(envPath: string, updates: Record<string, string>): Promise<void> {
  const existing = await readEnvFile(envPath);
  const merged = { ...existing, ...updates };
  await writeEnvFile(envPath, merged);
}

/**
 * Get .env path for global or project scope
 */
export function getEnvPath(projectPath?: string): string {
  if (projectPath) {
    return path.join(projectPath, 'auto-claude', '.env');
  }
  return path.join(os.homedir(), '.auto-claude', '.env');
}
