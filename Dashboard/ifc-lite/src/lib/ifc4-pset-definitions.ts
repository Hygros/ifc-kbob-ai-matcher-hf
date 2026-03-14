/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * IFC4 Property Set definitions — standard psets applicable to entity types.
 *
 * This provides schema-aware property suggestions for the property editor.
 * Based on the IFC4 ADD2 TC1 specification.
 */

import { PropertyValueType } from '@ifc-lite/data';

export interface PsetDefinition {
  name: string;
  description: string;
  applicableTypes: string[];
}

export interface PsetPropertyDef {
  name: string;
  description: string;
  type: PropertyValueType;
}

/** Classification systems commonly used in the AEC industry */
export const CLASSIFICATION_SYSTEMS: Array<{ name: string; description: string }> = [
  { name: 'Uniclass', description: 'UK unified classification for the construction industry' },
  { name: 'OmniClass', description: 'North American construction classification' },
  { name: 'MasterFormat', description: 'CSI specification division numbering' },
  { name: 'UniFormat', description: 'Building systems classification' },
  { name: 'ICS', description: 'International Classification for Standards' },
  { name: 'CCS', description: 'CCI Construction Classification System' },
  { name: 'SfB', description: 'Swedish SfB classification system' },
  { name: 'NBS Create', description: 'NBS specification system' },
  { name: 'eBKP-H', description: 'Swiss building cost classification' },
  { name: 'CBI', description: 'Custom classification' },
];

// ── Standard IFC4 Property Sets ──

const PSET_WALL_COMMON: PsetDefinition = {
  name: 'Pset_WallCommon',
  description: 'Common properties for walls',
  applicableTypes: ['IfcWall', 'IfcWallStandardCase'],
};

const PSET_SLAB_COMMON: PsetDefinition = {
  name: 'Pset_SlabCommon',
  description: 'Common properties for slabs',
  applicableTypes: ['IfcSlab', 'IfcSlabStandardCase'],
};

const PSET_COLUMN_COMMON: PsetDefinition = {
  name: 'Pset_ColumnCommon',
  description: 'Common properties for columns',
  applicableTypes: ['IfcColumn', 'IfcColumnStandardCase'],
};

const PSET_BEAM_COMMON: PsetDefinition = {
  name: 'Pset_BeamCommon',
  description: 'Common properties for beams',
  applicableTypes: ['IfcBeam', 'IfcBeamStandardCase'],
};

const PSET_DOOR_COMMON: PsetDefinition = {
  name: 'Pset_DoorCommon',
  description: 'Common properties for doors',
  applicableTypes: ['IfcDoor'],
};

const PSET_WINDOW_COMMON: PsetDefinition = {
  name: 'Pset_WindowCommon',
  description: 'Common properties for windows',
  applicableTypes: ['IfcWindow'],
};

const PSET_COVERING_COMMON: PsetDefinition = {
  name: 'Pset_CoveringCommon',
  description: 'Common properties for coverings',
  applicableTypes: ['IfcCovering'],
};

const PSET_ROOF_COMMON: PsetDefinition = {
  name: 'Pset_RoofCommon',
  description: 'Common properties for roofs',
  applicableTypes: ['IfcRoof'],
};

const PSET_STAIRFLIGHT_COMMON: PsetDefinition = {
  name: 'Pset_StairFlightCommon',
  description: 'Common properties for stair flights',
  applicableTypes: ['IfcStairFlight'],
};

const PSET_RAILING_COMMON: PsetDefinition = {
  name: 'Pset_RailingCommon',
  description: 'Common properties for railings',
  applicableTypes: ['IfcRailing'],
};

const PSET_RAMP_COMMON: PsetDefinition = {
  name: 'Pset_RampCommon',
  description: 'Common properties for ramps',
  applicableTypes: ['IfcRamp'],
};

const PSET_CURTAINWALL_COMMON: PsetDefinition = {
  name: 'Pset_CurtainWallCommon',
  description: 'Common properties for curtain walls',
  applicableTypes: ['IfcCurtainWall'],
};

const PSET_PLATE_COMMON: PsetDefinition = {
  name: 'Pset_PlateCommon',
  description: 'Common properties for plates',
  applicableTypes: ['IfcPlate'],
};

const PSET_MEMBER_COMMON: PsetDefinition = {
  name: 'Pset_MemberCommon',
  description: 'Common properties for members',
  applicableTypes: ['IfcMember'],
};

const PSET_PILE_COMMON: PsetDefinition = {
  name: 'Pset_PileCommon',
  description: 'Common properties for piles',
  applicableTypes: ['IfcPile'],
};

const PSET_FOOTING_COMMON: PsetDefinition = {
  name: 'Pset_FootingCommon',
  description: 'Common properties for footings',
  applicableTypes: ['IfcFooting'],
};

const PSET_SPACE_COMMON: PsetDefinition = {
  name: 'Pset_SpaceCommon',
  description: 'Common properties for spaces',
  applicableTypes: ['IfcSpace'],
};

const PSET_BUILDING_ELEMENT_PROXY_COMMON: PsetDefinition = {
  name: 'Pset_BuildingElementProxyCommon',
  description: 'Common properties for building element proxies',
  applicableTypes: ['IfcBuildingElementProxy'],
};

const ALL_PSETS: PsetDefinition[] = [
  PSET_WALL_COMMON,
  PSET_SLAB_COMMON,
  PSET_COLUMN_COMMON,
  PSET_BEAM_COMMON,
  PSET_DOOR_COMMON,
  PSET_WINDOW_COMMON,
  PSET_COVERING_COMMON,
  PSET_ROOF_COMMON,
  PSET_STAIRFLIGHT_COMMON,
  PSET_RAILING_COMMON,
  PSET_RAMP_COMMON,
  PSET_CURTAINWALL_COMMON,
  PSET_PLATE_COMMON,
  PSET_MEMBER_COMMON,
  PSET_PILE_COMMON,
  PSET_FOOTING_COMMON,
  PSET_SPACE_COMMON,
  PSET_BUILDING_ELEMENT_PROXY_COMMON,
];

// ── Common property definitions per pset ──

const COMMON_PROPERTIES: Record<string, PsetPropertyDef[]> = {
  Pset_WallCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'AcousticRating', description: 'Acoustic rating', type: PropertyValueType.Label },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'Combustible', description: 'Whether combustible', type: PropertyValueType.Boolean },
    { name: 'SurfaceSpreadOfFlame', description: 'Surface spread of flame', type: PropertyValueType.Label },
    { name: 'ThermalTransmittance', description: 'U-value', type: PropertyValueType.Real },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'LoadBearing', description: 'Whether load bearing', type: PropertyValueType.Boolean },
    { name: 'ExtendToStructure', description: 'Whether extends to structure', type: PropertyValueType.Boolean },
  ],
  Pset_SlabCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'AcousticRating', description: 'Acoustic rating', type: PropertyValueType.Label },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'Combustible', description: 'Whether combustible', type: PropertyValueType.Boolean },
    { name: 'ThermalTransmittance', description: 'U-value', type: PropertyValueType.Real },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'LoadBearing', description: 'Whether load bearing', type: PropertyValueType.Boolean },
  ],
  Pset_ColumnCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'LoadBearing', description: 'Whether load bearing', type: PropertyValueType.Boolean },
    { name: 'Slope', description: 'Column slope angle', type: PropertyValueType.Real },
  ],
  Pset_BeamCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'LoadBearing', description: 'Whether load bearing', type: PropertyValueType.Boolean },
    { name: 'Span', description: 'Clear span', type: PropertyValueType.Real },
    { name: 'Slope', description: 'Beam slope angle', type: PropertyValueType.Real },
  ],
  Pset_DoorCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'AcousticRating', description: 'Acoustic rating', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'FireExit', description: 'Whether fire exit', type: PropertyValueType.Boolean },
    { name: 'SelfClosing', description: 'Whether self-closing', type: PropertyValueType.Boolean },
    { name: 'SmokeStop', description: 'Whether smoke stop', type: PropertyValueType.Boolean },
    { name: 'HandicapAccessible', description: 'Handicap accessible', type: PropertyValueType.Boolean },
    { name: 'ThermalTransmittance', description: 'U-value', type: PropertyValueType.Real },
  ],
  Pset_WindowCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'AcousticRating', description: 'Acoustic rating', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'ThermalTransmittance', description: 'U-value', type: PropertyValueType.Real },
    { name: 'GlazingAreaFraction', description: 'Glazing fraction', type: PropertyValueType.Real },
    { name: 'SmokeStop', description: 'Whether smoke stop', type: PropertyValueType.Boolean },
  ],
  Pset_CoveringCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'AcousticRating', description: 'Acoustic rating', type: PropertyValueType.Label },
    { name: 'Combustible', description: 'Whether combustible', type: PropertyValueType.Boolean },
    { name: 'FlammabilityRating', description: 'Flammability rating', type: PropertyValueType.Label },
    { name: 'Finish', description: 'Surface finish', type: PropertyValueType.Label },
  ],
  Pset_RoofCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'ThermalTransmittance', description: 'U-value', type: PropertyValueType.Real },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
  ],
  Pset_StairFlightCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'NumberOfRiser', description: 'Number of risers', type: PropertyValueType.Integer },
    { name: 'NumberOfTreads', description: 'Number of treads', type: PropertyValueType.Integer },
    { name: 'RiserHeight', description: 'Riser height', type: PropertyValueType.Real },
    { name: 'TreadLength', description: 'Tread length', type: PropertyValueType.Real },
  ],
  Pset_RailingCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'Height', description: 'Railing height', type: PropertyValueType.Real },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
  ],
  Pset_RampCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'HandicapAccessible', description: 'Handicap accessible', type: PropertyValueType.Boolean },
    { name: 'RequiredSlope', description: 'Required slope', type: PropertyValueType.Real },
  ],
  Pset_CurtainWallCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'ThermalTransmittance', description: 'U-value', type: PropertyValueType.Real },
    { name: 'AcousticRating', description: 'Acoustic rating', type: PropertyValueType.Label },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
  ],
  Pset_PlateCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'LoadBearing', description: 'Whether load bearing', type: PropertyValueType.Boolean },
    { name: 'AcousticRating', description: 'Acoustic rating', type: PropertyValueType.Label },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'ThermalTransmittance', description: 'U-value', type: PropertyValueType.Real },
  ],
  Pset_MemberCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'LoadBearing', description: 'Whether load bearing', type: PropertyValueType.Boolean },
    { name: 'FireRating', description: 'Fire resistance rating', type: PropertyValueType.Label },
    { name: 'Span', description: 'Clear span', type: PropertyValueType.Real },
    { name: 'Slope', description: 'Member slope angle', type: PropertyValueType.Real },
  ],
  Pset_PileCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'LoadBearing', description: 'Whether load bearing', type: PropertyValueType.Boolean },
  ],
  Pset_FootingCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'LoadBearing', description: 'Whether load bearing', type: PropertyValueType.Boolean },
  ],
  Pset_SpaceCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
    { name: 'IsExternal', description: 'Whether external', type: PropertyValueType.Boolean },
    { name: 'GrossPlannedArea', description: 'Gross planned area', type: PropertyValueType.Real },
    { name: 'NetPlannedArea', description: 'Net planned area', type: PropertyValueType.Real },
    { name: 'PubliclyAccessible', description: 'Whether publicly accessible', type: PropertyValueType.Boolean },
    { name: 'HandicapAccessible', description: 'Handicap accessible', type: PropertyValueType.Boolean },
  ],
  Pset_BuildingElementProxyCommon: [
    { name: 'Reference', description: 'Type reference', type: PropertyValueType.Identifier },
    { name: 'Status', description: 'Element status', type: PropertyValueType.Label },
  ],
};

/**
 * Get standard property set definitions applicable to a given IFC entity type.
 */
export function getPsetDefinitionsForType(entityType: string, _schemaVersion?: string): PsetDefinition[] {
  return ALL_PSETS.filter(pset =>
    pset.applicableTypes.some(t =>
      entityType === t || entityType === t + 'StandardCase',
    ),
  );
}

/**
 * Get property definitions for a named property set.
 */
export function getPropertiesForPset(psetName: string): PsetPropertyDef[] {
  return COMMON_PROPERTIES[psetName] ?? [];
}
