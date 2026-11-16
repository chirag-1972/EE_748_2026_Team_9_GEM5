#include "mem/cache/replacement_policies/lru9_rp.hh"

#include <algorithm>
#include <cassert>
#include <memory>

#include "params/LRU9RP.hh"

namespace gem5
{

namespace replacement_policy
{

LRU9::LRU9(const Params &p) : Base(p)
{}

void
LRU9::registerEntry(LRU9ReplData *entry) const
{
    auto &entries = setEntries[entry->set];
    if (std::find(entries.begin(), entries.end(), entry) == entries.end()) {
        entries.push_back(entry);
    }
}

void
LRU9::invalidate(const std::shared_ptr<ReplacementData> &replacement_data)
{
    assert(replacement_data);
    auto entry = std::static_pointer_cast<LRU9ReplData>(replacement_data);
    entry->valid = false;
    entry->rank = 15;
}

void
LRU9::promote(LRU9ReplData *entry) const
{
    registerEntry(entry);
    const uint8_t old_rank = entry->rank;
    for (auto candidate : setEntries[entry->set]) {
        if (candidate->valid && candidate->rank < old_rank) {
            ++candidate->rank;
        }
    }
    entry->rank = 0;
}

void
LRU9::touch(const std::shared_ptr<ReplacementData> &replacement_data) const
{
    assert(replacement_data);
    auto entry = std::static_pointer_cast<LRU9ReplData>(replacement_data);
    if (entry->valid) {
        promote(entry.get());
    }
}

void
LRU9::insert(LRU9ReplData *entry) const
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
LRU9::reset(const std::shared_ptr<ReplacementData> &replacement_data) const
{
    assert(replacement_data);
    insert(std::static_pointer_cast<LRU9ReplData>(replacement_data).get());
}

ReplaceableEntry *
LRU9::getVictim(const ReplacementCandidates &candidates) const
{
    assert(!candidates.empty());

    for (auto candidate : candidates) {
        auto entry =
            std::static_pointer_cast<LRU9ReplData>(candidate->replacementData);
        entry->set = candidate->getSet();
        registerEntry(entry.get());
    }

    for (auto candidate : candidates) {
        auto entry =
            std::static_pointer_cast<LRU9ReplData>(candidate->replacementData);
        if (!entry->valid) {
            return candidate;
        }
    }

    return *std::max_element(
        candidates.begin(), candidates.end(),
        [](const auto lhs, const auto rhs) {
            return std::static_pointer_cast<LRU9ReplData>(lhs->replacementData)
                       ->rank <
                   std::static_pointer_cast<LRU9ReplData>(rhs->replacementData)
                       ->rank;
        });
}

std::shared_ptr<ReplacementData>
LRU9::instantiateEntry()
{
    return std::make_shared<LRU9ReplData>();
}

} // namespace replacement_policy
} // namespace gem5
