import { id } from 'ethers';
export const POLYGON_CHAIN_ID = 137;
export const POLYGON_HYPERSYNC_URL = 'https://polygon.hypersync.xyz';

// Official deployed exchange contracts on Polygon (Chain ID 137)
export const CTF_EXCHANGE_V1 = '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E';
export const NEGRISK_CTF_EXCHANGE_V1 = '0xC5d563A36AE78145C45a50134d48A1215220f80a';
export const CTF_EXCHANGE_V2 = '0xE111180000d2663C0091e4f400237545B87B996B';
// https://docs.polymarket.com/resources/contracts verified 2026-09-09.
export const NEGRISK_CTF_EXCHANGE_V2 = '0xe2222d279d744050d28e00520010520000310F59';

// Official Derived Event Topics
// V1: OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)
export const ORDER_FILLED_V1_TOPIC = id('OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)');
// V2: OrderFilled(bytes32,address,address,uint8,uint256,uint256,uint256,uint256,bytes32,bytes32)
export const ORDER_FILLED_V2_TOPIC = id('OrderFilled(bytes32,address,address,uint8,uint256,uint256,uint256,uint256,bytes32,bytes32)');

// Backwards-compatible topic export
export const ORDER_FILLED_TOPIC = ORDER_FILLED_V1_TOPIC;
export const ALL_ORDER_FILLED_TOPICS = [ORDER_FILLED_V1_TOPIC, ORDER_FILLED_V2_TOPIC];

export const ALL_EXCHANGE_ADDRESSES = [
  CTF_EXCHANGE_V1,
  NEGRISK_CTF_EXCHANGE_V1,
  CTF_EXCHANGE_V2,
  NEGRISK_CTF_EXCHANGE_V2,
];
