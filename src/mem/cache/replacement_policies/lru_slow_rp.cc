// Team 9

#include "mem/cache/replacement_policies/lru_slow_rp.hh"

#include <cassert>
#include <memory>

#include "params/LRUSlow.hh"

namespace gem5
{
namespace replacement_policy
{

LRUSlow::LRUSlow(const LRUSlowParams &params)
    : Base(params), numWays(params.num_ways), createdEntries(0)
{
    assert(numWays > 0);
}

std::shared_ptr<ReplacementData>
LRUSlow::instantiateEntry()
{
    // This Classic cache creates entries consecutively by set and way.
    if (createdEntries % numWays == 0) {
        currentSet = std::make_shared<SetState>();
    }

    auto data = std::make_shared<SlottedData>(currentSet);
    currentSet->ways.push_back(data.get());

    ++createdEntries;
    return data;
}

void
LRUSlow::touch(const std::shared_ptr<ReplacementData> &replacement_data) const
{
    std::shared_ptr<SlottedData> data =
        std::static_pointer_cast<SlottedData>(replacement_data);

    assert(data->set != nullptr);
    assert(data->valid);

    if (data->priority == 0) {
        return; // Already MRU.
    }

    int old_priority = data->priority;
    int new_priority = old_priority - 1;
    SlottedData *neighbor = nullptr;

    for (const auto &candidate_data : data->set->ways) {
        if (candidate_data != data.get() && candidate_data->valid &&
            candidate_data->priority == new_priority) {
            neighbor = candidate_data;
            break;
        }
    }

    assert(neighbor != nullptr);

    data->priority = new_priority;
    neighbor->priority = old_priority;
}
void
LRUSlow::reset(const std::shared_ptr<ReplacementData> &replacement_data) const
{
    std::shared_ptr<SlottedData> data =
        std::static_pointer_cast<SlottedData>(replacement_data);

    assert(data->set != nullptr);
    assert(!data->valid);

    // Make room at MRU by shifting valid entries toward LRU.
    for (const auto &candidate_data : data->set->ways) {
        if (candidate_data != data.get() && candidate_data->valid) {
            candidate_data->priority++;
        }
    }

    data->priority = 0;
    data->valid = true;
}
void
LRUSlow::invalidate(const std::shared_ptr<ReplacementData> &replacement_data)
{
    std::shared_ptr<SlottedData> data =
        std::static_pointer_cast<SlottedData>(replacement_data);

    assert(data->set != nullptr);

    if (!data->valid) {
        return;
    }

    int old_priority = data->priority;
    data->valid = false;

    // Close the gap left by this entry.
    for (const auto &candidate_data : data->set->ways) {
        if (candidate_data != data.get() && candidate_data->valid &&
            candidate_data->priority > old_priority) {
            candidate_data->priority--;
        }
    }
}
ReplaceableEntry *
LRUSlow::getVictim(const ReplacementCandidates &candidates) const
{
    assert(!candidates.empty());

    ReplaceableEntry *victim = nullptr;
    int max_priority = -1;

    for (const auto &candidate : candidates) {
        std::shared_ptr<SlottedData> data =
            std::static_pointer_cast<SlottedData>(candidate->replacementData);

        if (!data->valid) {
            return candidate; // Fill an empty entry first.
        }

        if (data->priority > max_priority) {
            max_priority = data->priority;
            victim = candidate;
        }
    }

    return victim;
}
} // namespace replacement_policy
} // namespace gem5
