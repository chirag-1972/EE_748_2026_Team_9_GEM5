/**
 * Explicit-rank LRU replacement policy with LRU-9 insertion.
 */

#ifndef __MEM_CACHE_REPLACEMENT_POLICIES_LRU9_RP_HH__
#define __MEM_CACHE_REPLACEMENT_POLICIES_LRU9_RP_HH__

#include <cstdint>
#include <unordered_map>
#include <vector>

#include "mem/cache/replacement_policies/base.hh"

namespace gem5
{

struct LRU9RPParams;

namespace replacement_policy
{

class LRU9 : public Base
{
  protected:
    struct LRU9ReplData : ReplacementData
    {
        uint8_t rank;
        uint32_t set;
        bool valid;

        LRU9ReplData() : rank(15), set(0), valid(false) {}
    };

    mutable std::unordered_map<uint32_t, std::vector<LRU9ReplData *>>
        setEntries;

    void registerEntry(LRU9ReplData *entry) const;
    void promote(LRU9ReplData *entry) const;
    void insert(LRU9ReplData *entry) const;

  public:
    typedef LRU9RPParams Params;
    LRU9(const Params &p);
    ~LRU9() = default;

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

#endif // __MEM_CACHE_REPLACEMENT_POLICIES_LRU9_RP_HH__
