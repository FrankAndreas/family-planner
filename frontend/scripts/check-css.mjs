// The wall iPad's Safari may be older than 16.4, which doesn't understand media range syntax (`width>=48rem`):
// such a query never matches there, so md:hidden etc. would silently stop working. Run after `npm run build`.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const dir = join(import.meta.dirname, '..', 'dist', 'assets');
const css = readdirSync(dir).filter((name) => name.endsWith('.css'));
if (!css.length) {
    console.error('check-css: no built CSS in dist/assets (run npm run build first)');
    process.exit(1);
}
const bad = css.flatMap((name) => readFileSync(join(dir, name), 'utf8').match(/@media[^{]*(<=|>=|<|>)[^{]*\{/g) ?? []);
if (bad.length) {
    console.error(`check-css: media range syntax old Safari can't read:\n  ${[...new Set(bad)].join('\n  ')}`);
    process.exit(1);
}
console.log('check-css: ok');
