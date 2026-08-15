/**
 * Package-owned invariant companion for `dsh-logtimeline`.
 * @module dsh-logtimeline/invariant
 */

import type { Context } from '@deepseek-ai/cordis'

const PACKAGE_NAME = 'dsh-logtimeline'

/** A package-attributed invariant failure reported by the host registry. */
type InvariantFailure = (message: string) => never

/** Installer callback accepted by the host's invariant registry. */
type InvariantInstaller = (ctx: Context, fail: InvariantFailure) => void | Promise<void>

/** Minimal runtime contract used by the companion without a source checkout. */
interface InvariantRegistry {
  register(packageName: string, installer: InvariantInstaller): () => void
}

/** Cordis companion plugin name. */
export const name = 'logtimeline-invariant'
/** Service required before the companion can reserve package ownership. */
export const inject = ['invariants']

/**
 * No runtime invariant: the plugin owns no mutable data relation beyond the
 * tool registration itself (effect-based, auto-unwound on unload).
 */
const install: InvariantInstaller = () => {}

/**
 * Resolve the host registry through Cordis's named service lookup. Keeping this
 * narrow local contract lets the plugin build without host source files; a
 * composed DSH profile still supplies the real `invariants` service.
 */
function getInvariantRegistry(ctx: Context): InvariantRegistry {
  const registry = ctx.get('invariants') as InvariantRegistry | undefined
  if (registry === undefined) {
    throw new Error(`invariant companion requires the "invariants" service for ${PACKAGE_NAME}`)
  }
  return registry
}

/** Register this package's invariant companion. */
export const apply = (ctx: Context): Promise<() => void> =>
  Promise.resolve(getInvariantRegistry(ctx).register(PACKAGE_NAME, install))
