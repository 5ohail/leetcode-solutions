class Solution {
public:
    vector<int> searchRange(vector<int>& nums, int target) {
        int first = -1, last = -1;
        int high = nums.size() -1, low = 0;
        while(low <= high){
            int mid = low + (high - low)/2;
            if(low <= high &&nums[mid] == target){
                if( mid > 0 && nums[mid] == nums[mid-1]) high = mid - 1;
                else {first = mid; break;}
            }
            else if(nums[mid] < target) low = mid + 1;
            else high = mid - 1;
        }
        if(first == -1) return{-1,-1};
        low = first; high = nums.size() - 1;
        while(low <= high){
            int mid = low + (high - low)/2;
            if(low <= high && nums[mid] == target){
                if( mid + 1 < nums.size() && nums[mid] == nums[mid+1]) low = mid + 1;
                else{last = mid;break;}
            }
            else if(nums[mid] > target) high = mid - 1;
            else low = mid+1;
        }


        return {first,last};
    }
};