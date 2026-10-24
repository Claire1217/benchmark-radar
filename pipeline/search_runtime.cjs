// One persistent process per Python SearchIndex; no shell interpolation or eval.
const readline=require('node:readline'),Search=require('../web/search.js');
let records=null;
readline.createInterface({input:process.stdin,crlfDelay:Infinity}).on('line',line=>{
 try{const request=JSON.parse(line);if(request.records){records=request.records;for(const r of records)Search.prepare(r);process.stdout.write('{"ready":true}\n');}
 else {if(!records)throw new Error('Search not initialized');process.stdout.write(JSON.stringify(Search.search(records,request.query,request.alternatives||[]))+'\n');}}
 catch(error){process.stdout.write(JSON.stringify({error:error.message})+'\n');}
});
