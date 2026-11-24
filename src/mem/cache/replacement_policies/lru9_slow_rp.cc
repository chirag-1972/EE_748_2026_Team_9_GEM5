#include "mem/cache/replacement_policies/lru9_slow_rp.hh"

#include <algorithm>
#include <cassert>
#include <memory>

#include "params/LRU9_Slow_RP.hh"

namespace gem5
{

namespace replacement_policy
{

LRU9_Slow::LRU9_Slow(const Params &p) : Base(p)
{}

void
LRU9_Slow::registerEntry(LRU9_Slow_ReplData *entry) const
{
    auto &entries = setEntries[entry->set];
    if (std::find(entries.begin(), entries.end(), entry) == entries.end()) {
        entries.push_back(entry);
    }
}

void
LRU9_Slow::invalidate(const std::shared_ptr<ReplacementData> &replacement_data)
{
    assert(replacement_data);
    auto entry =
        std::static_pointer_cast<LRU9_Slow_ReplData>(replacement_data);
    entry->valid = false;
    entry->rank = 15;
}

void
LRU9_Slow::promote(LRU9_Slow_ReplData *entry) const
{
    registerEntry(entry);
    const uint8_t old_rank = entry->rank;

    if (old_rank == 0) {
        return; // Already MRU.
    }

    LRU9_Slow_ReplData *neighbor = nullptr;

    const uint8_t new_rank = old_rank - 1;
    for (auto candidate : setEntries[entry->set]) {
        if (candidate != entry && candidate->valid &&
            candidate->rank == new_rank) {
            // ++candidate->rank;
            neighbor = candidate;
            break;
        }
    }

    assert(neighbor != nullptr);

    neighbor->rank = old_rank;
    entry->rank = new_rank;
}

void
LRU9_Slow::touch(
    const std::shared_ptr<ReplacementData> &replacement_data) const
{
    assert(replacement_data);
    auto entry =
        std::static_pointer_cast<LRU9_Slow_ReplData>(replacement_data);
    if (entry->valid) {
        promote(entry.get());
    }
}

void
LRU9_Slow::insert(LRU9_Slow_ReplData *entry) const
{
    registerEntry(entry);
    auto &entries = setEntries[entry->set];
    const uint8_t valid_count =
        std::count_if(entries.begin(), entries.end(),
                      [](const auto candidate) { return candidate->valid; });
    // LRU-9 is rank 6 when rank 15 is the LRU position.
    const uint8_t target = std::min<uint8_t>(6, valid_count);

    for (auto candidate : entries) {
        if (candidate != entry && candidate->valid &&
            candidate->rank >= target) {
            ++candidate->rank;
        }
    }
    entry->rank = target;
    entry->valid = true;
}

void
LRU9_Slow::reset(
    const std::shared_ptr<ReplacementData> &replacement_data) const
{
    assert(replacement_data);
    insert(
        std::static_pointer_cast<LRU9_Slow_ReplData>(replacement_data).get());
}

ReplaceableEntry *
LRU9_Slow::getVictim(const ReplacementCandidates &candidates) const
{
    assert(!candidates.empty());

    for (auto candidate : candidates) {
        auto entry = std::static_pointer_cast<LRU9_Slow_ReplData>(
            candidate->replacementData);
        entry->set = candidate->getSet();
        registerEntry(entry.get());
    }

    for (auto candidate : candidates) {
        auto entry = std::static_pointer_cast<LRU9_Slow_ReplData>(
            candidate->replacementData);
        if (!entry->valid) {
            return candidate;
        }
    }

    return *std::max_element(
        candidates.begin(), candidates.end(),
        [](const auto lhs, const auto rhs) {
            return std::static_pointer_cast<LRU9_Slow_ReplData>(
                       lhs->replacementData)
                       ->rank < std::static_pointer_cast<LRU9_Slow_ReplData>(
                                    rhs->replacementData)
                                    ->rank;
        });
}

std::shared_ptr<ReplacementData>
LRU9_Slow::instantiateEntry()
{
    return std::make_shared<LRU9_Slow_ReplData>();
}

} // namespace replacement_policy
} // namespace gem5
