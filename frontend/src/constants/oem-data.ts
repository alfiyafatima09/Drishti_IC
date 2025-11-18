/**
 * OEM (Original Equipment Manufacturer) data
 */

export const OEM_MANUFACTURERS = [
  'Texas Instruments',
  'STMicroelectronics',
  'NXP Semiconductors',
  'Analog Devices',
  'Infineon Technologies',
  'Microchip',
  'Intel',
  'AMD',
  'Broadcom',
  'Qualcomm',
] as const;

export type OEMManufacturer = typeof OEM_MANUFACTURERS[number];

export const OEM_COLORS = {
  'Texas Instruments': '#CC0000',
  'STMicroelectronics': '#03234B',
  'NXP Semiconductors': '#0066CC',
  'Analog Devices': '#007ACC',
  'Infineon Technologies': '#00897B',
  'Microchip': '#DC0714',
} as const;

