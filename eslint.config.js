import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: ["dist/", "node_modules/", "docs/", "public/", "art-source/", "art-export/"],
  },

  // TypeScript source and tests: type-aware rules catch real bugs (missed awaits, unsafe any).
  {
    files: ["src/**/*.ts", "tests/**/*.ts", "*.config.ts"],
    extends: [js.configs.recommended, ...tseslint.configs.recommendedTypeChecked],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
      globals: globals.browser,
    },
    rules: {
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      eqeqeq: ["error", "always"],
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },

  // Node scripts in tools/ and this config file.
  {
    files: ["tools/**/*.mjs", "eslint.config.js"],
    extends: [js.configs.recommended],
    languageOptions: {
      globals: globals.node,
    },
  },
);
