// Team 9

#ifndef __MEM_CACHE_REPLACEMENT_POLICIES_LRU_SLOW_RP_HH__
#define __MEM_CACHE_REPLACEMENT_POLICIES_LRU_SLOW_RP_HH__

#include <cstdint>
#include <memory>
#include <vector>

#include "mem/cache/replacement_policies/base.hh"

namespace gem5
{

struct LRUSlowParams;

namespace replacement_policy
{

class LRUSlow : public Base
{
  protected:
    struct SlottedData;

    // One shared object for all ways in one cache set.
    struct SetState
    {
        std::vector<SlottedData *> ways;
    };

    // One object for each cache entry.
    struct SlottedData : ReplacementData
    {
        std::shared_ptr<SetState> set;
        int priority;
        bool valid;

        explicit SlottedData(std::shared_ptr<SetState> set_state)
            : set(set_state), priority(0), valid(false)
        {}
    };

    const uint32_t numWays;
    uint64_t createdEntries;
    std::shared_ptr<SetState> currentSet;

  public:
    typedef LRUSlowParams Params;

    explicit LRUSlow(const Params &params);
    ~LRUSlow() = default;

    void invalidate(
        const std::shared_ptr<ReplacementData> &replacement_data) override;

    void touch(const std::shared_ptr<ReplacementData> &replacement_data)
        const override;

    void reset(const std::shared_ptr<ReplacementData> &replacement_data)
        const override;

    ReplaceableEntry *
    getVictim(const ReplacementCandidates &candidates) const override;

    std::shared_ptr<ReplacementData> instantiateEntry() override;
};

} // namespace replacement_policy
} // namespace gem5

#endif
