class Solution {
public:
    int countElements(vector<int>& nums) {
        int minElem = *min_element(begin(nums),end(nums));
        int maxElem = *max_element(begin(nums),end(nums));
        int ans = 0;
        for(int x : nums){
            if(x > minElem && x < maxElem){
                ans++;
            }
        }
        return ans;
    }
};