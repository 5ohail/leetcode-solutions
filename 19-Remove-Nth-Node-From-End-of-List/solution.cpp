/**
 * Definition for singly-linked list.
 * struct ListNode {
 *     int val;
 *     ListNode *next;
 *     ListNode() : val(0), next(nullptr) {}
 *     ListNode(int x) : val(x), next(nullptr) {}
 *     ListNode(int x, ListNode *next) : val(x), next(next) {}
 * };
 */
class Solution {
public:
    int target;
    int countNodes(ListNode* head){
        if(head->next == NULL) return 1;
        else{
            return 1 + countNodes(head->next);
        }
    }
    void removeNode(ListNode* head,int count){
        if(count == target-1 && head->next != NULL){
            head->next = head->next->next;
        }
        else if(head->next != NULL){
            removeNode(head->next,count+1);
        }
        else return;
    }
    ListNode* removeNthFromEnd(ListNode* head, int n) {
        if(countNodes(head) == n) return head->next;
        n = countNodes(head) - n;
        if(head->next == NULL) return NULL;
        
        target = n;
        removeNode(head,0);
        return head;
    }
};