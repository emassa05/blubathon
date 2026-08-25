/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // SPEC 3: `apps/web` solo consume contratos publicados por la API. No abre
  // SQLite ni carga artefactos Python.
  eslint: { dirs: ["app", "components", "lib", "tests"] },
};

export default nextConfig;
