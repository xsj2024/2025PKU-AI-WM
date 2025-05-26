import cv2
import os
from typing import Union, Optional, Dict
import numpy as np

class RelicMatcher:
    def __init__(self, relic_dir: str = "relic_images/", min_feature_threshold: int = 52):
        """
        Initialize the RelicMatcher with ORB feature extraction.
        
        Args:
            relic_dir: Directory containing relic images (default: "relic_images/")
            min_feature_threshold: Minimum number of features required in database images (default: 100)
        """
        self.relic_db: Dict[str, Optional[np.ndarray]] = {}
        self.min_feature_threshold = min_feature_threshold
        self.orb = cv2.ORB_create(
            nfeatures=200,
            scaleFactor=1.2,
            edgeThreshold=5,
            patchSize=20
        )
        self._load_relics(relic_dir)
    
    def _load_relics(self, relic_dir: str) -> None:
        """
        Load and extract ORB features from all relic images in the directory.
        Only store images with feature count above the threshold.
        
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
                    kp, des = self.orb.detectAndCompute(gray, None)
                    if des is not None and len(kp) >= self.min_feature_threshold:
                        self.relic_db[name] = des
                    else:
                        print(f"Warning: Image {img_file} has insufficient features ({len(kp) if kp else 0} < {self.min_feature_threshold})")
                else:
                    print(f"Warning: Could not read image {img_file}")
    
    def match(
        self, 
        input_image: Union[str, np.ndarray], 
        ratio_thresh: float = 0.7,  # Adjusted for binary descriptors
        show_matches: bool = False
    ) -> str:
        """
        Match a test image against the relic database.
        
        Args:
            input_image: Path to image file OR in-memory image array
            ratio_thresh: Lowe's ratio test threshold (default: 0.7)
            show_matches: Whether to display matched keypoints (default: False)
            
        Returns:
            Name of matched relic or "Unknown" if no match found
        """
        # Calculate match threshold as 25% of the min_feature_threshold
        threshold = max(int(self.min_feature_threshold * 0.25), 1)
        
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
        test_kp, test_des = self.orb.detectAndCompute(test_gray, None)
        
        if test_des is None:
            print("Warning: No features detected in test image")
            return "Unknown"
        
        # Find best match in database
        best_match = None
        best_score = 0
        best_good_matches = []
        best_db_kp = None
        
        bf = cv2.BFMatcher(cv2.NORM_HAMMING)  # Hamming distance for binary descriptors
        
        for name, des in self.relic_db.items():
            if des is None:
                continue
                
            matches = bf.knnMatch(test_des, des, k=2)
            good = []
            
            # Apply ratio test
            try:  # Some ORB matches might not have enough pairs
                for m, n in matches:
                    if m.distance < ratio_thresh * n.distance:
                        good.append(m)
            except ValueError:
                continue
            
            score = len(good)
            
            if score > best_score:
                best_score = score
                best_match = name
                best_good_matches = good
                
                # For visualization if needed
                if show_matches:
                    db_img = cv2.imread(f"relic_images/{name}.jpg")
                    db_gray = cv2.cvtColor(db_img, cv2.COLOR_BGR2GRAY)
                    _, best_db_kp = self.orb.detectAndCompute(db_gray, None)
        
        # Optional visualization
        if show_matches and best_match and best_db_kp is not None:
            db_img = cv2.imread(f"relic_images/{best_match}.jpg")
            img_matches = cv2.drawMatches(
                test_img, test_kp,
                db_img, best_db_kp,
                best_good_matches[:50], None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
            )
            cv2.imshow("Matches", img_matches)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        print(f"Best match score: {best_score}, Threshold: {threshold}")
        return best_match if best_score > threshold else "Unknown"

if __name__ == '__main__':
    relic = RelicMatcher()
    img = cv2.imread("img_matcher/bcc5224a-c651-40e0-9d22-f1fca2537e65.png")

    import time
    t = time.time()
    for i in range(1):
        print(relic.match(img))
    print(time.time()-t)
