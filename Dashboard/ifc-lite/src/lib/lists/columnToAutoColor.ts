/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * Convert a list column definition into a lens auto-color spec.
 * This allows "color by column" from the list results table.
 */

import type { ColumnDefinition } from '@ifc-lite/lists';
import type { AutoColorSpec } from '@ifc-lite/lens';

export function columnToAutoColor(col: ColumnDefinition): AutoColorSpec {
  return {
    source: col.source as AutoColorSpec['source'],
    psetName: col.psetName,
    propertyName: col.propertyName,
  };
}
