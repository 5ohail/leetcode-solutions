class Solution {
public:
    int arrSum(vector<int>& nums){
        int sum = 0;
        for(int x : nums){
            sum += x;
        }
        return sum;
    }
    int checkDays(vector<int>& wt,int& mid){
        int day = 1, load = 0;
        for(int i = 0;i<wt.size();i++){
            if(load + wt[i] > mid){
                day++;
                load = wt[i];
            }
            else{
                load += wt[i];
            }
        }
        return day;
    }
    int shipWithinDays(vector<int>& weights, int days) {
        int left = *max_element(begin(weights),end(weights));
        int right = arrSum(weights);
        int ans = 0;
        while(left<=right){
            int mid = left + (right-left)/2;
            int reqDays = checkDays(weights,mid);
            if(reqDays <= days){
                ans = mid;
                right = mid-1;
            }
            else{
                left = mid+1;
            }
        }
        return ans;
    }
};