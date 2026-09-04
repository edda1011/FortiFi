module fortifi_protection::protection_policy;

use sui::event;
use sui::clock::Clock;
use sui::table::{Self, Table};

const E_NOT_ADMIN: u64 = 0;
const E_ALREADY_RECORDED: u64 = 1;

public struct Registry has key {
    id: UID,
    admin: address,
    recorded: Table<address, bool>,
}

public struct ProtectionRecord has key, store {
    id: UID,
    report_hash: address,
    base_wallet: address,
    signature: vector<u8>,
    base_transaction: vector<u8>,
    created_at_ms: u64,
}

public struct RecordCreated has copy, drop {
    report_hash: address,
    base_wallet: address,
    record_id: ID,
}

fun init(ctx: &mut TxContext) {
    transfer::share_object(Registry {
        id: object::new(ctx),
        admin: ctx.sender(),
        recorded: table::new(ctx),
    });
}

entry fun create_record(
    registry: &mut Registry,
    report_hash: address,
    base_wallet: address,
    signature: vector<u8>,
    base_transaction: vector<u8>,
    clock: &Clock,
    ctx: &mut TxContext,
) {
    assert!(ctx.sender() == registry.admin, E_NOT_ADMIN);
    assert!(!registry.recorded.contains(report_hash), E_ALREADY_RECORDED);
    registry.recorded.add(report_hash, true);

    let record = ProtectionRecord {
        id: object::new(ctx),
        report_hash,
        base_wallet,
        signature,
        base_transaction,
        created_at_ms: clock.timestamp_ms(),
    };
    let record_id = object::id(&record);
    event::emit(RecordCreated { report_hash, base_wallet, record_id });
    transfer::public_transfer(record, ctx.sender());
}

public fun was_recorded(registry: &Registry, report_hash: address): bool {
    registry.recorded.contains(report_hash)
}
