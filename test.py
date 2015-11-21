import unittest
import getpass
from grenier.helpers import *
from grenier.grenier import Grenier


class TestClass(unittest.TestCase):

    def setUp(self):
        self.grenier = Grenier(Path("test_files", "test.yaml"))

    def tearDown(self):
        del self.grenier

    def test_1_open_config(self):
        self.assertTrue(self.grenier.open_config())
        self.assertIsNotNone(self.grenier.repositories)
        self.assertEqual(len(self.grenier.repositories), 1)

        # repositories
        test_repo = self.grenier.repositories[0]
        self.assertEqual(test_repo.name, "test1")
        self.assertEqual(test_repo.backup_dir, Path("test_files/backup/bup_test1"))
        self.assertTrue(test_repo.backup_dir.exists())
        self.assertEqual(test_repo.passphrase, "test1_passphrase")

        # sources
        self.assertEqual(len(test_repo.sources), 2)
        for source in test_repo.sources:
            self.assertIn(source.name, ["folder1", "folder2"])
            if source.name == "folder1":
                self.assertEqual(source.target_dir, Path("test_files/folder1"))
                self.assertListEqual(source.excluded_extensions, ["ignored"])
            else:
                self.assertEqual(source.target_dir, Path("test_files/folder2"))
                self.assertListEqual(source.excluded_extensions, [])

        # remotes
        self.assertEqual(len(test_repo.remotes), 3)

    def test_2_save(self):
        self.grenier.open_config()
        for r in self.grenier.repositories:
            number_of_files = r.backup(display=False)
            self.assertEqual(number_of_files, 5)
            repo_contents = [str(el) for el in r.backup_dir.rglob("*")]
            self.assertNotEqual(len(repo_contents), 0)

    def test_3_fuse(self):
        self.grenier.open_config()
        for r in self.grenier.repositories:
            r.fuse(str(r.temp_dir), display=False)
            fuse_contents = [str(el.relative_to(r.temp_dir)) for el in r.temp_dir.rglob("*")]
            self.assertNotEqual(len(fuse_contents), 0)
            for s in r.sources:
                self.assertTrue(s.name in fuse_contents)
                # verifying contents
                if s.name == "folder1":
                    self.assertTrue("folder1/latest/test1.txt" in fuse_contents)
                    self.assertFalse("folder1/latest/test2.ignored" in fuse_contents)
                if s.name == "folder2":
                    self.assertTrue("folder2/latest/test3.txt" in fuse_contents)
                    self.assertTrue("folder2/latest/test4.ignored" in fuse_contents)

    def test_4_unfuse(self):
        self.grenier.open_config()
        for r in self.grenier.repositories:
            r.unfuse(r.temp_dir, display=False)
            fuse_contents = [str(el) for el in r.temp_dir.rglob("*")]
            self.assertEqual(len(fuse_contents), 0)
            self.assertFalse(is_fuse_mounted(r.temp_dir))

    def test_5_check(self):
        self.grenier.open_config()
        for r in self.grenier.repositories:
            out = r.check_and_repair(display=False)
            self.assertEqual(out, [])
            # TODO what else to check?

    def test_6_sync_to_folder(self):
        self.grenier.open_config()
        for r in self.grenier.repositories:
            self.assertFalse(r.sync_remote("pof", display=False))
            remote_path = Path("/tmp/grenier")
            self.assertTrue(r.sync_remote(str(remote_path), display=False))
            self.assertTrue(remote_path.exists())
            contents = [str(el) for el in remote_path.rglob("*")]
            self.assertNotEqual(len(contents), 0)
            # TODO other checks?
            # check sync yaml
            last_synced_yaml = Path(remote_path, "last_synced.yaml")
            self.assertTrue(last_synced_yaml.exists())
            # TODO check contents?

    def test_7_sync_to_disk(self):
        self.grenier.open_config()
        for r in self.grenier.repositories:
            self.assertFalse(r.sync_remote("pof", display=False))

            # needs external disk connected, skip if not present
            remote_path = Path("/run/media/%s/%s" % (getpass.getuser(), "DISK1"))
            if remote_path.exists():
                self.assertTrue(r.sync_remote("DISK1", display=False))

                contents = [str(el) for el in remote_path.rglob("*")]
                self.assertNotEqual(len(contents), 0)

                # TODO other checks?
                # check sync yaml
                last_synced_yaml = Path(remote_path, "last_synced.yaml")
                self.assertTrue(last_synced_yaml.exists())
                # TODO check contents?

                # TODO cleanup

    def test_8_sync_to_hubic(self):
        # needs rclone config "test_cloud_container"
        self.grenier.open_config()
        for r in self.grenier.repositories:
            self.assertFalse(r.sync_remote("pof", display=False))

            found, remote = r._find_remote("test_cloud_container")
            self.assertTrue(found)
            self.assertTrue(remote.is_known)
            self.assertTrue(remote.is_cloud)

            self.assertTrue(r.sync_remote("test_cloud_container", display=False))
            # testing encfs xml backup
            xml = Path(xdg.BaseDirectory.save_data_path("grenier"), "encfs_xml", "%s.xml" % r.name)
            self.assertTrue(xml.exists())
            # TODO test remote file size vs local?

            # cleanup: rclone purge test_cloud_container:test1?

    def test_sync_to_gdrive(self):
        pass

    def test_restore(self):
        pass

if __name__ == '__main__':
    unittest.main()