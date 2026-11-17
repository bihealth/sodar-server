import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      execArgv: [
        '--localstorage-file',
        path.resolve(os.tmpdir(), `vitest-${process.pid}.localstorage`),
      ],
      exclude: [...configDefaults.exclude, 'e2e/**'],
      globals: true,
      root: fileURLToPath(new URL('./', import.meta.url)),
      watch: false
    },
  }),
)
