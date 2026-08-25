/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // SPEC 3: `apps/web` solo consume contratos publicados por la API. No abre
  // SQLite ni carga artefactos Python.
  eslint: { dirs: ["app", "components", "lib", "tests"] },
  // `@faro/contract` es el paquete del workspace que publica H1 y se distribuye
  // como TypeScript sin compilar, así que Next lo transpila con el resto.
  transpilePackages: ["@faro/contract"],
};

export default nextConfig;
