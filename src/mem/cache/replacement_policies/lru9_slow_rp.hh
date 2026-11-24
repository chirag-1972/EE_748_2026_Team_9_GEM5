/**
 * Explicit-rank LRU replacement policy with LRU-9 Slow insertion.
 */

#ifndef __MEM_CACHE_REPLACEMENT_POLICIES_LRU9_SLOW_RP_HH__
#define __MEM_CACHE_REPLACEMENT_POLICIES_LRU9_SLOW_RP_HH__

#include <cstdint>
#include <unordered_map>
#include <vector>

#include "mem/cache/replacement_policies/base.hh"

namespace gem5
{

struct LRU9_Slow_RPParams;

namespace replacement_policy
{

class LRU9_Slow : public Base
{
  protected:
    struct LRU9_Slow_ReplData : ReplacementData
    {
        uint8_t rank;
        uint32_t set;
        bool valid;

        LRU9_Slow_ReplData() : rank(15), set(0), valid(false) {}
    };

    mutable std::unordered_map<uint32_t, std::vector<LRU9_Slow_ReplData *>>
        setEntries;

    void registerEntry(LRU9_Slow_ReplData *entry) const;
    void promote(LRU9_Slow_ReplData *entry) const;
    void insert(LRU9_Slow_ReplData *entry) const;

  public:
    typedef LRU9_Slow_RPParams Params;
    LRU9_Slow(const Params &p);
    ~LRU9_Slow() = default;

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

#endif // __MEM_CACHE_REPLACEMENT_POLICIES_LRU9_SLOW_RP_HH__
