class Solution {
public:
    int maxProduct(vector<int>& nums) {
        int maxi = INT_MIN;
        int pref = 1, suffix = 1;
        for(int i = 0;i<nums.size();i++){
            pref *= nums[i];
            suffix *= nums[nums.size()-1-i];
            maxi = max(suffix,max(maxi,pref));
            if(pref == 0) pref = 1;
            if(suffix == 0) suffix = 1;
        }
        return maxi;
    }
};