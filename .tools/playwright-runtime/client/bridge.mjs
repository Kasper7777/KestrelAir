import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const base=fileURLToPath(new URL('.',import.meta.url));
const transport=new StdioClientTransport({command:process.execPath,args:[base+'node_modules/@playwright/mcp/cli.js','--extension'],env:{...process.env},stderr:'inherit'});
const client=new Client({name:'simbrief-planner',version:'1.0'});
await client.connect(transport);
const tools=await client.listTools();
writeFileSync(base+'tools.json',JSON.stringify(tools,null,2));
console.log('READY '+tools.tools.map(t=>t.name).join(', '));
let last='';
while(true){
 if(existsSync(base+'request.json')){
  const raw=readFileSync(base+'request.json','utf8').replace(/^\uFEFF/,'');
  if(raw!==last){last=raw;const request=JSON.parse(raw);
   try {const result=await client.callTool(request);writeFileSync(base+'result.json',JSON.stringify(result,null,2));console.log('DONE '+request.name);}
   catch(e){writeFileSync(base+'result.json',JSON.stringify({error:e.message}));console.log('ERROR '+e.message);}
  }
 }
 await new Promise(r=>setTimeout(r,300));
}
