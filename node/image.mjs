// Nano Banana text-to-image from Node — OpenAI SDK images API.
//   npm i openai
//   export KUNAVO_API_KEY=sk-kn-...
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.KUNAVO_API_KEY,
  baseURL: "https://api.kunavo.com/v1",
});

const img = await client.images.generate({
  model: "nano-banana",
  prompt: "A neon ramen stall in the rain, cinematic, 35mm",
  size: "1024x1024",
});
// Temporary URL (~24h) — download and re-host.
console.log(img.data[0].url);
