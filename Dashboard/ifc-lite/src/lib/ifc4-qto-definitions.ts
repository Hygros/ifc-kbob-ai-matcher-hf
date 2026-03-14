/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * IFC4 Quantity Take-Off definitions — standard quantity sets for entity types.
 *
 * Based on the IFC4 ADD2 TC1 specification.
 */

import { QuantityType } from '@ifc-lite/data';

export interface QtoDefinition {
  name: string;
  description: string;
  applicableTypes: string[];
}

export interface QtoQuantityDef {
  name: string;
  description: string;
  type: QuantityType;
}

// ── Standard IFC4 Quantity Sets ──

const QTO_WALL: QtoDefinition = {
  name: 'Qto_WallBaseQuantities',
  description: 'Base quantities for walls',
  applicableTypes: ['IfcWall', 'IfcWallStandardCase'],
};

const QTO_SLAB: QtoDefinition = {
  name: 'Qto_SlabBaseQuantities',
  description: 'Base quantities for slabs',
  applicableTypes: ['IfcSlab', 'IfcSlabStandardCase'],
};

const QTO_COLUMN: QtoDefinition = {
  name: 'Qto_ColumnBaseQuantities',
  description: 'Base quantities for columns',
  applicableTypes: ['IfcColumn', 'IfcColumnStandardCase'],
};

const QTO_BEAM: QtoDefinition = {
  name: 'Qto_BeamBaseQuantities',
  description: 'Base quantities for beams',
  applicableTypes: ['IfcBeam', 'IfcBeamStandardCase'],
};

const QTO_DOOR: QtoDefinition = {
  name: 'Qto_DoorBaseQuantities',
  description: 'Base quantities for doors',
  applicableTypes: ['IfcDoor'],
};

const QTO_WINDOW: QtoDefinition = {
  name: 'Qto_WindowBaseQuantities',
  description: 'Base quantities for windows',
  applicableTypes: ['IfcWindow'],
};

const QTO_COVERING: QtoDefinition = {
  name: 'Qto_CoveringBaseQuantities',
  description: 'Base quantities for coverings',
  applicableTypes: ['IfcCovering'],
};

const QTO_SPACE: QtoDefinition = {
  name: 'Qto_SpaceBaseQuantities',
  description: 'Base quantities for spaces',
  applicableTypes: ['IfcSpace'],
};

const QTO_STAIRFLIGHT: QtoDefinition = {
  name: 'Qto_StairFlightBaseQuantities',
  description: 'Base quantities for stair flights',
  applicableTypes: ['IfcStairFlight'],
};

const QTO_RAILING: QtoDefinition = {
  name: 'Qto_RailingBaseQuantities',
  description: 'Base quantities for railings',
  applicableTypes: ['IfcRailing'],
};

const QTO_RAMP: QtoDefinition = {
  name: 'Qto_RampFlightBaseQuantities',
  description: 'Base quantities for ramp flights',
  applicableTypes: ['IfcRampFlight'],
};

const QTO_PLATE: QtoDefinition = {
  name: 'Qto_PlateBaseQuantities',
  description: 'Base quantities for plates',
  applicableTypes: ['IfcPlate'],
};

const QTO_MEMBER: QtoDefinition = {
  name: 'Qto_MemberBaseQuantities',
  description: 'Base quantities for members',
  applicableTypes: ['IfcMember'],
};

const QTO_FOOTING: QtoDefinition = {
  name: 'Qto_FootingBaseQuantities',
  description: 'Base quantities for footings',
  applicableTypes: ['IfcFooting'],
};

const QTO_PILE: QtoDefinition = {
  name: 'Qto_PileBaseQuantities',
  description: 'Base quantities for piles',
  applicableTypes: ['IfcPile'],
};

const ALL_QTOS: QtoDefinition[] = [
  QTO_WALL, QTO_SLAB, QTO_COLUMN, QTO_BEAM, QTO_DOOR, QTO_WINDOW,
  QTO_COVERING, QTO_SPACE, QTO_STAIRFLIGHT, QTO_RAILING, QTO_RAMP,
  QTO_PLATE, QTO_MEMBER, QTO_FOOTING, QTO_PILE,
];

// ── Quantity definitions per QTO set ──

const QTO_QUANTITIES: Record<string, QtoQuantityDef[]> = {
  Qto_WallBaseQuantities: [
    { name: 'Length', description: 'Wall length', type: QuantityType.Length },
    { name: 'Width', description: 'Wall width/thickness', type: QuantityType.Length },
    { name: 'Height', description: 'Wall height', type: QuantityType.Length },
    { name: 'GrossSideArea', description: 'Gross side area', type: QuantityType.Area },
    { name: 'NetSideArea', description: 'Net side area', type: QuantityType.Area },
    { name: 'GrossFootprintArea', description: 'Gross footprint area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
    { name: 'GrossWeight', description: 'Gross weight', type: QuantityType.Weight },
    { name: 'NetWeight', description: 'Net weight', type: QuantityType.Weight },
  ],
  Qto_SlabBaseQuantities: [
    { name: 'Width', description: 'Slab width', type: QuantityType.Length },
    { name: 'Length', description: 'Slab length', type: QuantityType.Length },
    { name: 'Depth', description: 'Slab depth/thickness', type: QuantityType.Length },
    { name: 'Perimeter', description: 'Slab perimeter', type: QuantityType.Length },
    { name: 'GrossArea', description: 'Gross area', type: QuantityType.Area },
    { name: 'NetArea', description: 'Net area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
    { name: 'GrossWeight', description: 'Gross weight', type: QuantityType.Weight },
    { name: 'NetWeight', description: 'Net weight', type: QuantityType.Weight },
  ],
  Qto_ColumnBaseQuantities: [
    { name: 'Length', description: 'Column length', type: QuantityType.Length },
    { name: 'CrossSectionArea', description: 'Cross-section area', type: QuantityType.Area },
    { name: 'OuterSurfaceArea', description: 'Outer surface area', type: QuantityType.Area },
    { name: 'GrossSurfaceArea', description: 'Gross surface area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
    { name: 'GrossWeight', description: 'Gross weight', type: QuantityType.Weight },
    { name: 'NetWeight', description: 'Net weight', type: QuantityType.Weight },
  ],
  Qto_BeamBaseQuantities: [
    { name: 'Length', description: 'Beam length', type: QuantityType.Length },
    { name: 'CrossSectionArea', description: 'Cross-section area', type: QuantityType.Area },
    { name: 'OuterSurfaceArea', description: 'Outer surface area', type: QuantityType.Area },
    { name: 'GrossSurfaceArea', description: 'Gross surface area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
    { name: 'GrossWeight', description: 'Gross weight', type: QuantityType.Weight },
    { name: 'NetWeight', description: 'Net weight', type: QuantityType.Weight },
  ],
  Qto_DoorBaseQuantities: [
    { name: 'Width', description: 'Door width', type: QuantityType.Length },
    { name: 'Height', description: 'Door height', type: QuantityType.Length },
    { name: 'Perimeter', description: 'Door perimeter', type: QuantityType.Length },
    { name: 'Area', description: 'Door area', type: QuantityType.Area },
  ],
  Qto_WindowBaseQuantities: [
    { name: 'Width', description: 'Window width', type: QuantityType.Length },
    { name: 'Height', description: 'Window height', type: QuantityType.Length },
    { name: 'Perimeter', description: 'Window perimeter', type: QuantityType.Length },
    { name: 'Area', description: 'Window area', type: QuantityType.Area },
  ],
  Qto_CoveringBaseQuantities: [
    { name: 'Width', description: 'Covering width', type: QuantityType.Length },
    { name: 'GrossArea', description: 'Gross area', type: QuantityType.Area },
    { name: 'NetArea', description: 'Net area', type: QuantityType.Area },
  ],
  Qto_SpaceBaseQuantities: [
    { name: 'Height', description: 'Space height', type: QuantityType.Length },
    { name: 'FinishFloorHeight', description: 'Finish floor height', type: QuantityType.Length },
    { name: 'GrossFloorArea', description: 'Gross floor area', type: QuantityType.Area },
    { name: 'NetFloorArea', description: 'Net floor area', type: QuantityType.Area },
    { name: 'GrossWallArea', description: 'Gross wall area', type: QuantityType.Area },
    { name: 'NetWallArea', description: 'Net wall area', type: QuantityType.Area },
    { name: 'GrossCeilingArea', description: 'Gross ceiling area', type: QuantityType.Area },
    { name: 'NetCeilingArea', description: 'Net ceiling area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
  ],
  Qto_StairFlightBaseQuantities: [
    { name: 'Length', description: 'Stair flight length', type: QuantityType.Length },
    { name: 'GrossArea', description: 'Gross area', type: QuantityType.Area },
    { name: 'NetArea', description: 'Net area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
  ],
  Qto_RailingBaseQuantities: [
    { name: 'Length', description: 'Railing length', type: QuantityType.Length },
  ],
  Qto_RampFlightBaseQuantities: [
    { name: 'Length', description: 'Ramp flight length', type: QuantityType.Length },
    { name: 'Width', description: 'Ramp flight width', type: QuantityType.Length },
    { name: 'GrossArea', description: 'Gross area', type: QuantityType.Area },
    { name: 'NetArea', description: 'Net area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
  ],
  Qto_PlateBaseQuantities: [
    { name: 'Width', description: 'Plate width', type: QuantityType.Length },
    { name: 'Length', description: 'Plate length', type: QuantityType.Length },
    { name: 'Depth', description: 'Plate depth/thickness', type: QuantityType.Length },
    { name: 'Perimeter', description: 'Plate perimeter', type: QuantityType.Length },
    { name: 'GrossArea', description: 'Gross area', type: QuantityType.Area },
    { name: 'NetArea', description: 'Net area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
    { name: 'GrossWeight', description: 'Gross weight', type: QuantityType.Weight },
    { name: 'NetWeight', description: 'Net weight', type: QuantityType.Weight },
  ],
  Qto_MemberBaseQuantities: [
    { name: 'Length', description: 'Member length', type: QuantityType.Length },
    { name: 'CrossSectionArea', description: 'Cross-section area', type: QuantityType.Area },
    { name: 'OuterSurfaceArea', description: 'Outer surface area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
    { name: 'GrossWeight', description: 'Gross weight', type: QuantityType.Weight },
    { name: 'NetWeight', description: 'Net weight', type: QuantityType.Weight },
  ],
  Qto_FootingBaseQuantities: [
    { name: 'Length', description: 'Footing length', type: QuantityType.Length },
    { name: 'Width', description: 'Footing width', type: QuantityType.Length },
    { name: 'Height', description: 'Footing height', type: QuantityType.Length },
    { name: 'CrossSectionArea', description: 'Cross-section area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
    { name: 'GrossWeight', description: 'Gross weight', type: QuantityType.Weight },
    { name: 'NetWeight', description: 'Net weight', type: QuantityType.Weight },
  ],
  Qto_PileBaseQuantities: [
    { name: 'Length', description: 'Pile length', type: QuantityType.Length },
    { name: 'CrossSectionArea', description: 'Cross-section area', type: QuantityType.Area },
    { name: 'OuterSurfaceArea', description: 'Outer surface area', type: QuantityType.Area },
    { name: 'GrossVolume', description: 'Gross volume', type: QuantityType.Volume },
    { name: 'NetVolume', description: 'Net volume', type: QuantityType.Volume },
    { name: 'GrossWeight', description: 'Gross weight', type: QuantityType.Weight },
    { name: 'NetWeight', description: 'Net weight', type: QuantityType.Weight },
  ],
};

/**
 * Get standard quantity set definitions applicable to a given IFC entity type.
 */
export function getQtoDefinitionsForType(entityType: string): QtoDefinition[] {
  return ALL_QTOS.filter(qto =>
    qto.applicableTypes.some(t =>
      entityType === t || entityType === t + 'StandardCase',
    ),
  );
}

/**
 * Get quantity definitions for a named quantity set.
 */
export function getQuantitiesForQto(qtoName: string): QtoQuantityDef[] {
  return QTO_QUANTITIES[qtoName] ?? [];
}

/**
 * Get unit string for a quantity type.
 */
export function getQuantityUnit(qtype: QuantityType): string {
  switch (qtype) {
    case QuantityType.Length: return 'm';
    case QuantityType.Area: return 'm²';
    case QuantityType.Volume: return 'm³';
    case QuantityType.Count: return '';
    case QuantityType.Weight: return 'kg';
    case QuantityType.Time: return 's';
    default: return '';
  }
}
