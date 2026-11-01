class Solution {
public:
    int findMin(vector<int>& nums) {
        int ans = INT_MAX;
        int LOW = 0, HIGH = nums.size()-1;
        while(LOW <= HIGH){
            int mid = LOW + (HIGH - LOW)/2;
            if(nums[LOW] <= nums[mid]){
                ans = min(ans,nums[LOW]);
                LOW = mid + 1;
            }
            else{
                ans = min(ans,nums[mid]);
                HIGH = mid - 1;
            }
        }
        return ans;
    }
};