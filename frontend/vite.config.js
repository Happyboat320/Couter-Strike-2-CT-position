import { defineConfig } from 'vite';
// 项目 Pages 使用仓库路径；克隆者可通过 VITE_BASE 指定自己的路径。
export default defineConfig({
  base: process.env.VITE_BASE || '/Couter-Strike-2-CT-position/',
});
