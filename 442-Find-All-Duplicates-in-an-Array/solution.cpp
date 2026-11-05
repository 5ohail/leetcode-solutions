class Solution {
public:
    vector<int> findDuplicates(vector<int>& nums) {
        vector<int> duplicate;
        for(int i = 0;i<nums.size();i++){
            int idx = abs(nums[i]) - 1;
            if(nums[idx] < 0){
                duplicate.push_back(idx+1);
            }
            else{
                nums[idx] = -nums[idx];
            }
        }
        return duplicate;
    }
};