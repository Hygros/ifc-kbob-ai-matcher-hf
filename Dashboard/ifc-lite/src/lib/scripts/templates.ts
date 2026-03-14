/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * Script templates — pre-defined scripts for common BIM automation tasks.
 */

export interface ScriptTemplate {
  name: string;
  description: string;
  code: string;
}

export const SCRIPT_TEMPLATES: ScriptTemplate[] = [
  {
    name: 'Count by Type',
    description: 'Count all entities grouped by IFC type',
    code: `// Count entities by IFC type
const all = bim.query.all()
const counts = {}
for (const e of all) {
  counts[e.type] = (counts[e.type] || 0) + 1
}
for (const [type, count] of Object.entries(counts).sort((a, b) => b[1] - a[1])) {
  console.log(type + ': ' + count)
}
`,
  },
  {
    name: 'List Walls',
    description: 'List all walls with their properties',
    code: `// List all walls
const walls = bim.query.byType('IfcWall')
console.log('Total walls:', walls.length)
for (const w of walls) {
  console.log(w.name || 'Unnamed', '- GlobalId:', w.globalId)
}
`,
  },
  {
    name: 'Find External Elements',
    description: 'Find elements marked as external',
    code: `// Find elements with IsExternal = true
const all = bim.query.all()
const external = all.filter(e => {
  const psets = e.propertySets()
  for (const ps of psets) {
    for (const p of ps.properties) {
      if (p.name === 'IsExternal' && p.value === true) return true
    }
  }
  return false
})
console.log('External elements:', external.length)
for (const e of external) {
  console.log(e.type, '-', e.name || 'Unnamed')
}
`,
  },
  {
    name: 'Model Summary',
    description: 'Generate a summary of the loaded model',
    code: `// Model summary
const models = bim.model.list()
console.log('Models:', models.length)
for (const m of models) {
  console.log('\\n📦', m.name)
  console.log('  Schema:', m.schemaVersion)
  console.log('  Entities:', m.entityCount)
}

const all = bim.query.all()
console.log('\\n--- Totals ---')
console.log('Entities:', all.length)

const types = new Set(all.map(e => e.type))
console.log('Unique types:', types.size)
`,
  },
];
