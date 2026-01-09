#!/usr/bin/env npx tsx
/**
 * Direct test of Azure Foundry connection with REAL values from project
 */

const API_KEY = process.env.AZURE_API_KEY || '';
const RESOURCE = process.env.AZURE_RESOURCE || '';

if (!API_KEY || !RESOURCE) {
  console.error('❌ Environment variables required:');
  console.error('   AZURE_API_KEY - Your Azure AI Services key');
  console.error('   AZURE_RESOURCE - Your Azure resource name');
  console.error('');
  console.error('   Usage: AZURE_API_KEY=xxx AZURE_RESOURCE=yyy npx tsx test-azure-direct.ts');
  process.exit(1);
}
const BASE_URL = `https://${RESOURCE}.services.ai.azure.com/anthropic`;

console.log('=== TESTE DIRETO AZURE FOUNDRY ===\n');
console.log('Valores:');
console.log(`  Resource: ${RESOURCE}`);
console.log(`  Base URL: ${BASE_URL}`);
console.log(`  API Key: ${API_KEY.slice(0, 10)}...${API_KEY.slice(-5)}`);
console.log('');

async function testConnection() {
  const endpoints = [
    `${BASE_URL}/v1/messages`,
    `https://${RESOURCE}.services.ai.azure.com/anthropic/v1/messages`,
    `https://${RESOURCE}.openai.azure.com/anthropic/v1/messages`,
  ];

  const headers_variations = [
    { name: 'api-key', headers: { 'api-key': API_KEY } },
    { name: 'x-api-key', headers: { 'x-api-key': API_KEY } },
    { name: 'Authorization Bearer', headers: { 'Authorization': `Bearer ${API_KEY}` } },
  ];

  for (const endpoint of endpoints) {
    console.log(`\n--- Testando: ${endpoint} ---\n`);
    
    for (const headerVar of headers_variations) {
      console.log(`  Header: ${headerVar.name}`);
      
      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            ...headerVar.headers,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: 'claude-haiku-4-5',
            max_tokens: 1,
            messages: [{ role: 'user', content: 'hi' }]
          }),
        });

        const text = await response.text();
        let json = null;
        try { json = JSON.parse(text); } catch {}

        console.log(`    Status: ${response.status} ${response.statusText}`);
        
        if (response.status === 200) {
          console.log(`    ✅ SUCESSO!`);
        } else if (response.status === 401 || response.status === 403) {
          console.log(`    ❌ AUTH FALHOU`);
        } else if (response.status === 404) {
          console.log(`    ⚠️  Endpoint não encontrado`);
        } else if (response.status === 400) {
          const errType = json?.error?.type || '';
          const errMsg = json?.error?.message || text.slice(0, 100);
          console.log(`    ⚠️  Bad Request: ${errType} - ${errMsg}`);
          if (errType === 'invalid_request_error' || errMsg.includes('model')) {
            console.log(`    ✅ (Auth funcionou, erro é de request/model)`);
          }
        } else {
          console.log(`    Body: ${text.slice(0, 200)}`);
        }
      } catch (err) {
        console.log(`    ❌ Erro: ${err.message}`);
      }
      console.log('');
    }
  }
}

testConnection().then(() => {
  console.log('\n=== FIM DO TESTE ===');
});
