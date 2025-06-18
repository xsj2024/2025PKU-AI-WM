import cv2
import os
from typing import Union, Optional, Dict
import numpy as np

class RelicMatcher:
    def __init__(self, relic_dir: str = "relic_images/"):
        """
        Initialize the RelicMatcher with SIFT feature extraction.
        
        Args:
            relic_dir: Directory containing relic images (default: "relic_images/")
        """
        self.relic_db: Dict[str, Optional[np.ndarray]] = {}
        self.sift = cv2.SIFT_create()
        self._load_relics(relic_dir)
    
    def _load_relics(self, relic_dir: str) -> None:
        """
        Load and extract SIFT features from all relic images in the directory.
        
        Args:
            relic_dir: Directory containing relic images
        """
        if not os.path.exists(relic_dir):
            raise FileNotFoundError(f"Relic directory not found: {relic_dir}")
        
        for img_file in os.listdir(relic_dir):
            if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(relic_dir, img_file)
                name = os.path.splitext(img_file)[0]
                img = cv2.imread(img_path)
                
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    _, des = self.sift.detectAndCompute(gray, None)
                    self.relic_db[name] = des
                else:
                    print(f"Warning: Could not read image {img_file}")
    
    def match(
        self, 
        input_image: Union[str, np.ndarray], 
        threshold: int = 20,
        ratio_thresh: float = 0.75,
        show_matches: bool = False
    ) -> str:
        """
        Match a test image against the relic database.
        
        Args:
            input_image: Path to image file OR in-memory image array
            threshold: Minimum number of good matches required (default: 20)
            ratio_thresh: Lowe's ratio test threshold (default: 0.75)
            show_matches: Whether to display matched keypoints (default: False)
            
        Returns:
            Name of matched relic or "Unknown" if no match found
        """
        # Handle different input types
        if isinstance(input_image, str):
            test_img = cv2.imread(input_image)
            if test_img is None:
                print(f"Error: Could not read image at {input_image}")
                return "Unknown"
        elif isinstance(input_image, np.ndarray):
            test_img = input_image
        else:
            raise ValueError("Input must be either image path or numpy array")
        
        # Extract features from test image
        test_gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
        test_kp, test_des = self.sift.detectAndCompute(test_gray, None)
        
        if test_des is None:
            print("Warning: No features detected in test image")
            return "Unknown"
        
        # Find best match in database
        best_match = None
        best_score = 0
        best_good_matches = []
        best_db_kp = None
        
        bf = cv2.BFMatcher()
        
        for name, des in self.relic_db.items():
            if des is None:
                continue
                
            matches = bf.knnMatch(test_des, des, k=2)
            good = []
            
            # Apply ratio test
            for m, n in matches:
                if m.distance < ratio_thresh * n.distance:
                    good.append(m)
            
            score = len(good)
            
            if score > best_score:
                best_score = score
                best_match = name
                best_good_matches = good
                
                # For visualization if needed
                if show_matches:
                    db_img = cv2.imread(f"relic_images/{name}.jpg")  # Adjust extension as needed
                    db_gray = cv2.cvtColor(db_img, cv2.COLOR_BGR2GRAY)
                    _, best_db_kp = self.sift.detectAndCompute(db_gray, None)
        
        # Optional visualization
        if show_matches and best_match:
            db_img = cv2.imread(f"relic_images/{best_match}.jpg")  # Adjust extension as needed
            img_matches = cv2.drawMatches(
                test_img, test_kp,
                db_img, best_db_kp,
                best_good_matches[:50], None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
            )
            cv2.imshow("Matches", img_matches)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        print(f"Best match score: {best_score}")
        return best_match if best_score > threshold else "Unknown"

if __name__ == '__main__':
    relic = RelicMatcher()
    img = cv2.imread("img_matcher/oddlysmoothstone.png")
    print(relic.match(img))