# The `tsc` prerequisite the step 3 gate depends on

Vitest's own type surface needs Node types and a modern `lib`, or `tsc --noEmit` fails inside `node_modules` (`Cannot find name 'Disposable' / 'setImmediate'`, `Cannot find type definition file for 'node'`) — errors that have nothing to do with your code and will block the gate on a fresh setup. The test lane needs:

```jsonc
// tsconfig.json
"lib": ["ESNext"],                       // Symbol.asyncDispose, used by rollup/vite types
"types": ["node", "vitest/globals"]      // + devDependency @types/node matching the Node major
```

Add `@types/node` at the **project's** Node major (24 → `@types/node@24`, 22 → `@types/node@22`) — a mismatched major reintroduces the same class of error.
