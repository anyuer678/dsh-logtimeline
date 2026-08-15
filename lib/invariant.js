/**
 * Package-owned invariant companion for `dsh-logtimeline`.
 * @module dsh-logtimeline/invariant
 */
const PACKAGE_NAME = 'dsh-logtimeline';
/** Cordis companion plugin name. */
export const name = 'logtimeline-invariant';
/** Service required before the companion can reserve package ownership. */
export const inject = ['invariants'];
/**
 * No runtime invariant: the plugin owns no mutable data relation beyond the
 * tool registration itself (effect-based, auto-unwound on unload).
 */
const install = () => { };
/**
 * Resolve the host registry through Cordis's named service lookup. Keeping this
 * narrow local contract lets the plugin build without host source files; a
 * composed DSH profile still supplies the real `invariants` service.
 */
function getInvariantRegistry(ctx) {
    const registry = ctx.get('invariants');
    if (registry === undefined) {
        throw new Error(`invariant companion requires the "invariants" service for ${PACKAGE_NAME}`);
    }
    return registry;
}
/** Register this package's invariant companion. */
export const apply = (ctx) => Promise.resolve(getInvariantRegistry(ctx).register(PACKAGE_NAME, install));
//# sourceMappingURL=invariant.js.map