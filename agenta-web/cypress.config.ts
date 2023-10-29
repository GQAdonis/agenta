import {defineConfig} from "cypress"

const OPENAI_API_KEY = process.env.CYPRESS_OPEN_AI_KEY || "your_api_key_here";

export default defineConfig({
    e2e: {
        baseUrl: "http://localhost",
        defaultCommandTimeout: 8000,
    },
    env: {
        baseApiURL: "http://localhost/api",
        OPENAI_API_KEY: OPENAI_API_KEY,
        localBaseUrl: "http://localhost",
        NEXT_PUBLIC_FF: false,
    },
})
