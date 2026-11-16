# CommonJS compatibility for Expo Router 57

Source: official `decode-uri-component@0.5.1` from the npm registry. MIT license retained in LICENSE. `upstream.mjs` is unmodified upstream code; decoder.cjs is an esbuild format conversion to CommonJS (target es2020). `index.cjs` exposes its default function to the CommonJS require used by query-string 7 in Expo Router 57. This avoids the vulnerable <=0.5.0 decoder without changing Expo's native SDK or upgrading query-string to an incompatible module interface.

To regenerate: esbuild transformSync(upstream, {format:'cjs', target:'es2020'}). No runtime Node APIs or extra network requests are introduced.
