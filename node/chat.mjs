// Claude via the OpenAI Node SDK — change baseURL, nothing else.
//   npm i openai
//   export KUNAVO_API_KEY=sk-kn-...
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.KUNAVO_API_KEY,
  baseURL: "https://api.kunavo.com/v1",
});

const resp = await client.chat.completions.create({
  model: "claude-sonnet-5",
  messages: [{ role: "user", content: "Explain quicksort in one paragraph." }],
});
console.log(resp.choices[0].message.content);
